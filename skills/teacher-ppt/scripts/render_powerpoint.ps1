param([Parameter(Mandatory=$true)][string]$Source,[Parameter(Mandatory=$true)][string]$OutputDir,[Parameter(Mandatory=$true)][string]$Scratch,[Parameter(Mandatory=$true)][string]$Report)
$ErrorActionPreference='Stop'
New-Item -ItemType Directory -Force -Path $OutputDir,$Scratch | Out-Null
$reportFull=[System.IO.Path]::GetFullPath($Report)
$reportDir=Split-Path -Parent $reportFull
$r=[ordered]@{status='pending';engine='PowerPoint';pptx_sha256=(Get-FileHash -LiteralPath $Source -Algorithm SHA256).Hash.ToLowerInvariant();pages=@();issues=@();native_edit_probe=$false;native_chart_edit_probe='not_applicable'}
$app=$null;$pres=$null;$wb=$null;$probe=$null;$initial=0
try{
 $app=New-Object -ComObject PowerPoint.Application;$initial=$app.Presentations.Count
 $pres=$app.Presentations.Open($Source,-1,0,0)
 foreach($sl in $pres.Slides){
  $file=Join-Path $OutputDir ('slide-{0:D2}.png' -f $sl.SlideIndex);$sl.Export($file,'PNG',1600,900)
  foreach($sh in $sl.Shapes){
   if($sh.HasTextFrame -eq -1 -and $sh.TextFrame.HasText -eq -1){
    if($sh.TextFrame2.TextRange.BoundHeight -gt $sh.Height+3){$r.issues+=@{slide=$sl.SlideIndex;shape=$sh.Name;issue='text_height_overflow'}}
   }
   if($sh.HasTable -eq -1){for($ri=1;$ri -le $sh.Table.Rows.Count;$ri++){for($ci=1;$ci -le $sh.Table.Columns.Count;$ci++){
    $cell=$sh.Table.Cell($ri,$ci).Shape
    if($cell.TextFrame2.TextRange.BoundHeight -gt $cell.Height+3){$r.issues+=@{slide=$sl.SlideIndex;shape=$sh.Name;row=$ri;column=$ci;issue='table_text_overflow'}}
   }}}
  }
  $fileFull=[System.IO.Path]::GetFullPath($file)
  $relFile=if($fileFull.StartsWith($reportDir+'\',[System.StringComparison]::OrdinalIgnoreCase)){$fileFull.Substring($reportDir.Length+1).Replace('\','/')}else{$fileFull}
  $r.pages+=@{slide=$sl.SlideIndex;file=$relFile;sha256=(Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLowerInvariant()}
 }
 $pres.Close();$pres=$app.Presentations.Open($Source,0,-1,0)
 $target=$null;$targetIndex=0;$targetSlide=0
 $table=$null;$tableIndex=0;$tableSlide=0
 $chart=$null;$chartIndex=0;$chartSlide=0
 foreach($sl in $pres.Slides){
  for($si=1;$si -le $sl.Shapes.Count;$si++){
   $sh=$sl.Shapes.Item($si)
   if($null -eq $target -and $sh.HasTextFrame -eq -1 -and $sh.TextFrame.HasText -eq -1){$target=$sh;$targetIndex=$si;$targetSlide=$sl.SlideIndex}
   if($null -eq $table -and $sh.HasTable -eq -1){$table=$sh;$tableIndex=$si;$tableSlide=$sl.SlideIndex}
   if($null -eq $chart -and $sh.HasChart -eq -1){$chart=$sh;$chartIndex=$si;$chartSlide=$sl.SlideIndex}
  }
 }
 if($null -eq $target){throw 'No editable text'}
 $old=$target.Left;$target.TextFrame.TextRange.Text='teacher-edit-check';$target.Left=$old+8
 if($null -ne $table){$table.Table.Cell(1,1).Shape.TextFrame.TextRange.Text='teacher-table-check'}
 if($null -ne $chart){
  $chart.Chart.ChartData.Activate();$wb=$chart.Chart.ChartData.Workbook
  $wb.Worksheets.Item(1).Cells.Item(2,2).Value2=12345
  $wb.Close($true);$wb=$null
 }
 $probe=Join-Path $Scratch ('edit-probe-'+[guid]::NewGuid().ToString('N')+'.pptx');$pres.SaveAs($probe,24);$pres.Close();$pres=$app.Presentations.Open($probe,-1,0,0)
 $saved=$pres.Slides.Item($targetSlide).Shapes.Item($targetIndex)
 $r.native_edit_probe=($saved.TextFrame.TextRange.Text -eq 'teacher-edit-check' -and [math]::Abs($saved.Left-$old-8) -lt 0.1)
 if($null -ne $table){$r.native_edit_probe=$r.native_edit_probe -and ($pres.Slides.Item($tableSlide).Shapes.Item($tableIndex).Table.Cell(1,1).Shape.TextFrame.TextRange.Text -eq 'teacher-table-check')}
 if($null -ne $chart){
  $cs=$pres.Slides.Item($chartSlide).Shapes.Item($chartIndex)
  $cs.Chart.ChartData.Activate();$wb=$cs.Chart.ChartData.Workbook
  $val=$wb.Worksheets.Item(1).Cells.Item(2,2).Value2
  $wb.Close($false);$wb=$null
  $r.native_chart_edit_probe=($val -eq 12345)
 }
 $pres.Close();$pres=$null
 if((Get-FileHash -LiteralPath $Source -Algorithm SHA256).Hash.ToLowerInvariant() -ne $r.pptx_sha256){throw 'Source changed during render'}
 $chartOk=($null -eq $chart) -or ($r.native_chart_edit_probe -eq $true)
 $r.status=if($r.native_edit_probe -and $chartOk -and $r.issues.Count -eq 0){'passed'}else{'failed'}
}catch{$r.status='failed';$r.error=$_.Exception.Message}finally{
 if($null -ne $wb){try{$wb.Close($false)}catch{}}
 if($null -ne $pres){try{$pres.Close()}catch{}}
 if($null -ne $probe -and (Test-Path -LiteralPath $probe)){try{Remove-Item -LiteralPath $probe -Force -ErrorAction SilentlyContinue}catch{}}
 if($null -ne $app){if($initial -eq 0 -and $app.Presentations.Count -eq 0){$app.Quit()};[void][Runtime.InteropServices.Marshal]::ReleaseComObject($app)}
 $r | ConvertTo-Json -Depth 9 | Set-Content -LiteralPath $Report -Encoding UTF8
}
if($r.status -ne 'passed'){exit 1}
