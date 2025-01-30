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
        Write-Debug "Branch name is empty"
        return $false
    }
    if ( $branchName -eq 'dev' ) {
        Write-Debug "On dev branch"
        return $true
    }
    if ( $branchName.StartsWith('develop/') ) {
        Write-Debug "On develop/* branch"
        return $true
    }
    if ( $branchName.StartsWith('fix/') ) {
        Write-Debug "On fix/* branch"
        return $true
    }
    Write-Debug $githubref
    Write-Debug $branchName
    Write-Debug "Branch name was not recognized", $branchName

    return $false
}

function IsTag() {
	$githubref = $env:GITHUB_REF.Split('/')
	if ($githubref[1].ToLower() -ne 'tags') {
		return $false
	}
	return $true
}
