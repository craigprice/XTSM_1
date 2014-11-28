<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
<title>Untitled Document</title>
</head>

<body>
<script language="php">
$command="python_start.bat";
//exec('psexec.exe -accepteula -i -d "'.$command.'" 2>&1');
pclose(popen("start /B ". $command, "r"));
//exec($command,$output);
</script>
</body>
</html>
