. .\Scripts\utils.ps1

function IsDevelopmentBranch() {
	$githubref = $env:GITHUB_REF.Split('/')
    $refs = $githubref[1].ToLower()
	if ($refs -ne 'heads') {
        Write-Debug "Refs is not heads", $refs
		return $false
	}
	$branchName = $githubref[2]

    if ( [string]::IsNullOrEmpty($branchName)) {
        return $false
    }
    $allowed = @(
        'dev',
        'develop',
        'fix'
    )
    if ( $allowed -contains $branchName.ToLower() ) {
        return $true
    }

    return $false
}

function IsTag() {
	$githubref = $env:GITHUB_REF.Split('/')
	if ($githubref[1].ToLower() -ne 'tags') {
		return $false
	}
	return $true
}

function ValidateTag() {
	$githubref = $env:GITHUB_REF.Split('/')
	$verno = $githubref[2].Split('-')[0]
	$refdate = $githubref[2].Split('-')[1]
	$major = $verno.Split('.')[0]
	$minor = $verno.Split('.')[1]
	$release = $verno.Split('.')[2]
	if ($major -ne 'v3' -or [string]::IsNullOrEmpty($minor) -or [string]::IsNullOrEmpty($release) -or [string]::IsNullOrEmpty($refdate))
	{
		Write-Host "Invalid Tag format. Must be v3.0.3-20200101010101. Refusing to build!"
		exit 1
	}
	return $refdate
}
