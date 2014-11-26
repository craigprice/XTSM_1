<?php
	$port = $_REQUEST['port'];
    system("python_start.bat"." ".$port, $out);
?>