<?php
$filename = $_REQUEST['filename'];
$filedata = $_REQUEST['filedata'];

$folder=explode('/',$filename);
$number=count($folder);
for ($i=1; $i<$number; $i++) {
	$file = $folder[0];
	for ($j=1; $j<$i; $j++) {
		$file .= "/";
		$file .= $folder[$j];
		print $file;
	}
	If (!file_exists($file)) {mkdir($file);}
}
file_put_contents($filename, $filedata);
?>