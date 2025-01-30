. .\Scripts\utils.ps1

function IsDevelopmentBranch() {
	$githubref = $env:GITHUB_REF.Split('/')
	if ($githubref[1].ToLower() -ne 'heads') {
		return $false
	}
	$branchName = $githubref[2]

    if ( [string]::IsNullOrEmpty($branchName)) {
        return $false
    }
    if ( $branchName -eq 'dev' ) {
        return $true
    }
    if ( $branchName.StartsWith('develop/') ) {
        return $true
    }
    if ( $branchName.StartsWith('fix/') ) {
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
