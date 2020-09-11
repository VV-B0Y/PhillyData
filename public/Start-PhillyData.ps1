function Start-PhillyData {
	[CmdletBinding()]
	param ()

	Add-Type -AssemblyName @(
		'PresentationFramework'
		'PresentationCore'
		'WindowsBase'
		'System.Windows.Forms'
		'System.Drawing'
		'System'
		'System.Threading.Tasks'
	)

	foreach ($Assembly in (Get-ChildItem $PSScriptRoot/themes -Filter *.dll)) {
		[System.Reflection.Assembly]::LoadFrom($Assembly.fullName) | Out-Null
	}

	$Xaml = Get-Content -Path "$PSScriptRoot/PhillyDataGUI.xaml" -Raw

	#-------------------------------------------------------------#
	#----Control Event Handlers-----------------------------------#
	#-------------------------------------------------------------#
	#Write your code here
	$PPDSalarySet = @(
		'last_name'
		'first_name'
		'title'
		'annual_salary'
		'ytd_overtime_gross'
		'department'
		'calendar_year'
	)

	$ViolationSet = @(
		"opa_owner"
		"violationcodetitle"
		"address"
		"zip"
		"casetype"
		"casestatus"
		"caseprioritydesc"
		"violationdate"
		"violationstatus"
		"caseresponsibility"
	)

	$311Set = @(
		"opa_owner"
		"address"
		"zip"
		"complaintcodename"
		"complaintdate"
		"complaintstatus"
		"complaintnumber"
		"complaintcode"
		"ticket_num_311"
	)

	$CrimeSet = @(
		"dispatch_date"
		"dispatch_time"
		"location_block"
		"text_general_code"
		"dc_dist"
	)

	$311PcSet = @(
		"address"
		"requested_datetime"
		"status"
		"zipcode"
		"service_name"
		"agency_responsible"
		"service_notice"
		"status_notes"
		"media_url"
		"lat"
		"lon"
	)

	$PPDSalUri = "https://phl.carto.com/api/v2/sql?q=SELECT * FROM employee_salaries WHERE department = 'POLICE DEPARTMENT' AND calendar_year = 2019"
	$ViolationsURI = "https://phl.carto.com/api/v2/sql?q=SELECT * FROM violations WHERE casecreateddate >= current_date - 20 AND violationstatus = 'OPEN'"
	$311ComplaintUri = "https://phl.carto.com/api/v2/sql?q=SELECT * FROM complaints WHERE complaintdate >= current_date - 20"
	$311PublicCasesUri = "https://phl.carto.com/api/v2/sql?q=SELECT * FROM public_cases_fc WHERE requested_datetime >= current_date - 20"
	$CrimeUri = "https://phl.carto.com/api/v2/sql?q=SELECT * FROM incidents_part1_part2 WHERE dispatch_date_time >= current_date - 20"

	Function Get-Data {
		[CmdletBinding()]
		param (
			[Parameter(Mandatory)]
			[String]
			$Uri,
			[Parameter(Mandatory)]
			[String]
			$ColumnQuery,
			[Parameter(Mandatory)]
			[array]
			$ColumnSelection
		)

		$Script:Col = $ColumnQuery
		$Request = (Invoke-RestMethod $Uri).rows
		if ($ColumnSelection -NE 'PSCO') {
			$Script:Data = $Request | Select-Object $ColumnSelection | ConvertTo-DataTable
		}
		else {
			foreach ($Item in $Request) {
				[PSCustomObject]@{
					dispatch_date     = $Item.dispatch_date
					dispatch_time     = $Item.dispatch_time
					location_block    = $Item.location_block
					text_general_code = $Item.text_general_code
					dc_dist           = $Item.dc_dist
					Open_Map          = [hyperlink]('https://www.google.com/maps/@{0},{1},18z' -f $Item.point_y, $Item.point_x)
				}
			}
		}
	}

	$Username = 'admin'
	$Password = 'password'

	Function GoToLoginPage() {
		$MainWindow.title = 'login'
		$LoginFailedTB.Text = ""
		$TabNav.SelectedItem = $LoginTab
	}
	Function GoToLandingPage() {
		$TabNav.SelectedItem = $LandingTab
	}
	Function Login() {
		if ($UsernameTB.text -EQ $Username -and $PasswordTB.password -EQ $Password) {
			GoToLandingPage $this $_
		}
		Else {
			$LoginFailedTB.Text = 'login failed'
		}
	}
	Function DashClick() {
		$DashTab.SelectedItem = $DashboardTab
	}
	Function PPDClick() {
		$DashTab.SelectedItem = $PPDTab
	}


	#endregion
	#-------------------------------------------------------------#
	#----Script Execution-----------------------------------------#
	#-------------------------------------------------------------#

	$Window = [Windows.Markup.XamlReader]::Parse($Xaml)
	[xml]$xml = $Xaml
	$xml.SelectNodes("//*[@Name]") | ForEach-Object { Set-Variable -Name $_.Name -Value $Window.FindName($_.Name) }

	# Side Nav bindings

	$LoginBT.Add_Click( { Login $this $_ })
	$HomeBT.Add_Click( { GoToLoginPage $this $_ })
	<# 	$HomeBT.Add_Click( {
			DashClick $this $_
			$MainWindow.title = 'Dashboard'
			$Icon.Source = "C:\Users\$ENV:USERNAME\Pictures\PHL.png"
		}) #>
	$PPDBT.Add_Click( {
			PPDClick $this $_
			$MainWindow.title = 'City of Philadelphia Data'
			$Icon.Source = "C:\Users\$ENV:USERNAME\Pictures\Arrest.png"
		})
	# End side Nav Bindings

	# Button Actions
	$PPDGridBT.add_click( {
			$MainWindow.title = 'Philadelphia Police Dept. Salary Info: {0} records found' -f ($Data.Rows).count
			Get-Data -URI $PPDSalUri -ColumnQuery 'last_name' -ColumnSelection $PPDSalarySet
			$DataGrid.ItemsSource = $Data.DefaultView
		})
	$LiVGridBT.add_click( {
			$MainWindow.title = 'License and Inspections Violations: {0} records found' -f ($Data.Rows).count
			Get-Data -URI $ViolationsURI -ColumnQuery 'opa_owner' -ColumnSelection $ViolationSet
			$DataGrid.ItemsSource = $Data.DefaultView
		})
	$ComplaintsGridBT.add_click( {
			$MainWindow.title = '311 Complaints: {0} records found' -f ($Data.Rows).count
			Get-Data -URI $311ComplaintUri -ColumnQuery 'opa_owner' -ColumnSelection $311Set
			$DataGrid.ItemsSource = $Data.DefaultView
		})
	$PCGridBT.add_click( {
			$MainWindow.title = '311 Public Cases: {0} records found' -f ($Data.Rows).count
			Get-Data -URI $311PublicCasesUri -ColumnQuery 'address' -ColumnSelection $311pcSet
			$DataGrid.ItemsSource = $Data.DefaultView
		})
	$CrimeGridBT.add_click( {
			$MainWindow.title = 'Crime Data: {0} records found' -f ($Data.Rows).count
			Get-Data -URI $CrimeUri -ColumnQuery 'location_block' -ColumnSelection $CrimeSet
			$DataGrid.ItemsSource = $Data.DefaultView
		})

	$SearchTB.Add_TextChanged( {
			$InputText = $SearchTB.Text
			$filter = "$Col LIKE '%$InputText%'"
			$Data.DefaultView.RowFilter = $filter
			$DataGrid.ItemsSource = $Data.DefaultView
		})

	$Window.ShowDialog()
}