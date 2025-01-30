. .\Scripts\utils.ps1

function GetVersionFilePath($program)
{
	RequireProgram($program)
	$builddir = GetBuildDir($program)
	$VersionFilePath = "$builddir/Version.py"
	return $VersionFilePath
}

function GetVersionFileContents($program)
{
	RequireProgram($program)
	$VersionFile = GetVersionFilePath($program)
	if (!(Test-Path -Path $VersionFile))
	{
		Get-PSCallStack
		Write-Host "No version file at ", $VersionFile,". Aborting..."
		exit 1
	}

	$versionItem = Get-Content $VersionFile
	if ([string]::IsNullOrEmpty($versionItem))
	{
		Get-PSCallStack
		Write-Host "Version file at", $VersionFile, "is empty. Aborting..."
		exit 1
	}
	return $versionItem
}

function GetVersion($program)
{
	RequireProgram($program)
	$versionItem = GetVersionFileContents($program)
	Write-Host $program, "VersionItem for program", $program, "is", $versionItem
	$version = $versionItem.Split(' ')[1].Replace("`"", "")
	Write-Host $program, "Version is", $version
	return $version
}
