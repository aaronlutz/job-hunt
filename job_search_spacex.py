# Selinium Imports
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.options import Options
# SMTP (Email) Imports
import smtplib
from optparse import OptionParser
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.application import MIMEApplication
# Other Imports
from bs4 import BeautifulSoup
import time, os, json, sys, urllib, csv
from os import system
from datetime import date
from colorama import init
from termcolor import colored

def run_new_search(fresh_start=False, to_page=0):
	'''
	Searches for the lastest SpaceX Job Postings.
	'''
	init()
	setTerminal()

	# get config json
	with open('config.json') as c:
	    config = json.load(c)


	file_names = config["file_names"]

	print_header()
	printPrefrences()

	# Delete files to erase record of seen files
	# NOTE: This will treat ALL currently posted jobs as UNSEEN
	if fresh_start:
		delete_files(file_names)

	# Headless Driver
	print(colored('Starting Up', 'green'))
	print(colored('  creating headless firefox driver', 'white'))
	driver = get_driver(config)

	# Navigate for Search
	print(colored('  navigating to initial job search', 'white'))
	url = job_search_url()
	driver.get(url)

	# All Search Results
	search_results = get_search_results(driver)
	# Unseen Results
	unseen = []
	get_unseen_results(file_names, search_results, unseen)

	# Printed Unseen Summary
	if len(unseen) == 0:
		msg  = '\n░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░'
		msg += '\n░░ All Positions Previously Viewed ░░'
		msg += '\n░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░\n'
		print(msg)
	else:
		print_unseens(unseen)
		#screenshot_positions(driver, unseen)
		driver.quit()
		#send_emails(unseen)



def print_header():
	# print header
	msg  = '\n█████████████████████████'
	msg += '\n██   SpaceX Job Hunt   ██'
	msg += '\n█████████████████████████\n'
	print(colored(msg, 'green'))

def get_driver(config):
	'''
	Initialize and return headless firefox driver
	'''
	driver_path = config["driver_path"]
	options = Options()
	options.add_argument("--headless")
	driver = webdriver.Firefox(executable_path=driver_path, firefox_options=options)
	return driver

def job_search_url():
	'''create the spacex job search url'''

	# get urlparameters json
	with open('urlparameters.json') as c:
	    urlparameters = json.load(c)

	# unpack urlparameters json
	url_locations = urlparameters['Locations']
	url_departments = urlparameters['Departments']
	url_postionType = urlparameters['PositionType']
	base_url = urlparameters['BaseURL']

	# get urlparameters json
	with open('searchpreferences.json') as c:
	    searchpreferences = json.load(c)

	# unpack seas json
	pref_locations = searchpreferences['Locations']
	pref_departments = searchpreferences['Departments']
	pref_postionType = searchpreferences['PositionTypes']

	# Specify the URL
	url = 'http://www.spacex.com/careers/list'
	return url

def get_search_results(driver):
	'''Retrieve details about SpaceX job search and .'''
	print(colored('\nScrapping Search Results Page', 'green'))

	# Get HTML
	soup = BeautifulSoup(driver.page_source, 'lxml')
	dept_tbls = soup.find_all("table", {"class": "views-table cols-0"})
	jobs = []

	for t in range(0, len(dept_tbls)):
		# this department table
		dept_tbl = dept_tbls[t]
		# get department from the table caption
		department = dept_tbl.caption.contents[0].contents[0]
		# each job is a <tr> within the dept_tbl
		dept_jobs = dept_tbl.find_all("tr")

		# Populate array JOBS with a dictionary for each JOB
		for x in range(0, len(dept_jobs)):
			dept_job = dept_jobs[x]
			job = {}
			# Position
			job['title'] = dept_job.td.a.contents[0]
			# URL
			job['url'] = dept_job.td.a.get('href').strip()
			# Department comes from the tables caption
			job['department'] = department
			# ID
			job['id'] = job['url'][-10:]
			# Location
			location = dept_job.find_all('td')[1].div.contents[0].strip()
			job['location'] = location
			# Excel URL
			job['xl url'] = '=HYPERLINK("' + job['url'] + '", "View Online")'
			# relative url for the screenshot
			job['img_name'] = 'spacex_job_images/' + job['id'] + '.png'
			# todays date
			job['date'] = str(date.today())
			jobs.append(job)
	return jobs

def get_unseen_results(file_names, results, unseen):
	'''
	Update or Create the result ids csv file
	Append results whose ids arent already in the csv to unseen list
	'''
	# IDs from JSON (if it already exists)
	file_name = file_names['ids']
	if os.path.isfile(file_name) and os.stat(file_name).st_size != 0:
		# Load Seen Listing Details
		seen_results = read_from_csv(file_name)
		# IDs of Seen Listings
		seen_ids = [x['id'] for x in seen_results]
		# Populate Unseen Results List
		[unseen.append(r) for r in results if r['id'] not in seen_ids]
		# Append Unseen to File
		append_csv(seen_results+unseen, file_names['ids'])

	else:
		[unseen.append(r) for r in results]
		write_to_csv(unseen, file_names['ids'])
	# Update User
	print("  %-*s  %s" % (12, colored(len(results), 'red'), 'results'))
	print("  %-*s  %s" % (12, colored(len(unseen), 'red'), 'unseen'))

def screenshot_positions(driver, unseen):
	'''
	Screenshot SpaceX Job Positions
	'''
	print('\nScreenshotting Unseen Positions')
	l = len(unseen)
	for x in range(0, l):
		# Navigate and Get HTML
		driver.get(unseen[x]['url'])

		# Application Link ( the structure of the application pages headless
		# changed since this was fisrt written. Now the application is on the
		# bottom of the same page as the posting, whereas before it was on a
		# different page. I should remove)
		app = "" #driver.find_element_by_id('apply_button')
		unseen[x]['apply_url'] = "www.google.com" #app.get_attribute('href')
		# Screenshot
		element = driver.find_element_by_id('content')
		element_png = element.screenshot_as_png
		with open(unseen[x]['img_name'], "wb") as file:
			file.write(element_png)
		ProBar(x + 1, l, s = 'Complete\t' + str(unseen[x]['id']))

def send_emails(unseen):
	# add in "do you want an email for this?" input Loop
	# I'm tired of getting 20 emails a week for mostly jobs I don't care about
	# the printing of the seen jobs will need to be moved above the YN Loop
	# maybe a second print function should be called after the pruned Emails
	# have been sent, informing the user which were sent

	send_individual_emails(unseen)
	#if len(unseen) >= 10:
	#	send_preview_emails(unseen)
	#else:
	#	send_individual_emails(unseen)

def send_individual_emails(unseen):
	'''Send an Email with job details and screenshot of listing.'''
	print('\nSending Unseen Position Emails')

	# Get Email and Password from Credentials.JSON
	with open('credentials.json') as c:
	    credentials = json.load(c)

	FROM_EMAIL = credentials["email"]
	PASSWORD = credentials["password"]
	TO_EMAIL = credentials["email"]

	# Log into Email Server
	#server = smtplib.SMTP(host='smtp.mail.yahoo.com', port=587)
	server = smtplib.SMTP(host='smtp.gmail.com', port=587)
	server.ehlo()
	server.starttls()
	server.ehlo()
	server.login(FROM_EMAIL, PASSWORD)

	for x in range(0, len(unseen)):
		# Email Details
		msgRoot = MIMEMultipart('related')
		msgRoot['From'] = FROM_EMAIL
		msgRoot['To'] = TO_EMAIL
		_title = unseen[x]['title']
		_id = unseen[x]['id']
		msgRoot['Subject'] = 'SpaceX Job: ' + _title + ' (' + _id + ')'
		# Prepare Message HTML
		job_url = unseen[x]['url']
		app_url = unseen[x]['apply_url']
		html = """
			<p><a href=""" + job_url + """>View Position</a> &nbsp;
				<a href=""" + app_url + """>Apply</a><br/>
				<img src="cid:image1" width=924>
			</p>
		"""
		msgHtml = MIMEText(html, 'html')
		# Prepare Image
		img_name = unseen[x]['img_name']
		img = open(img_name, 'rb').read()
		msgImg = MIMEImage(img, 'png')
		msgImg.add_header('Content-ID', '<image1>')
		msgImg.add_header('Content-Disposition', 'inline', filename=img_name)
		# Attach MIME types to Message Root.
		msgRoot.attach(msgHtml)
		msgRoot.attach(msgImg)
		# Send the message via local SMTP server.
		failed_count = 0
		try:
			server.send_message(msgRoot)

		except smtplib.SMTPServerDisconnected:
			try:
				server.connect()
			except ConnectionRefusedError:
				failed_count += 1
				print('\n>>>>> CONNECTION REFUSED BY YAHOO <<<<<')
				break
			server.send_message(msgRoot)
		except smtplib.SMTPDataError:
			failed_count += 1

		ProBar(x + 1, len(unseen), s = 'Complete\t' + str(unseen[x]['id']))
	# Quit Server after Emails Sent
	if failed_count != 0:
		print('\t- ', failed_count, ' NOT SENT DUE TO DATA ERRORS')
	else:
		server.quit()


def delete_files(file_names, id_=True, pos=True, unseen=True):
	'''Delete files to prepare for a fresh start.'''
	# Identify Files to Delete
	files_to_delete = []
	if id_:
		files_to_delete.append(file_names['ids'])
	if pos:
		files_to_delete.append(file_names['pos'])
	if unseen:
		files_to_delete.append(file_names['unseen'])
	# Delete those Files
	for file_name in files_to_delete:
		pathname = os.path.dirname(sys.argv[0])
		folder_path = os.path.abspath(pathname)
		try:
			os.remove(folder_path + '\\' + file_name)
		except:
			pass

def printPrefrences():
	'''Print preferences found in searchpreferences.json'''

	# get urlparameters json
	with open('searchpreferences.json') as c:
	    searchpreferences = json.load(c)

	# unpack seas json
	loc = searchpreferences['Locations']
	dep = searchpreferences['Departments']
	typ = searchpreferences['PositionTypes']
	maxLen = max(len(loc), len(dep), len(typ))

	print(colored("\t%-*s" %
		(20, 'SEARCH PREFERENCES'), 'yellow'))
	print(colored("\t%-*s  %-*s  %s" %
		(20, 'JOB TYPES', 40, 'LOCATIONS', 'DEPARTMENTS'), 'green'))

	for x in range(0, maxLen):
		if (x >= len(loc)):
			l = ''
		else:
			l = loc[x]

		if (x >= len(dep)):
			d = ''
		else:
			d = dep[x]

		if (x >= len(typ)):
			t = ''
		else:
			t = typ[x]

		print("\t%-*s  %-*s  %s" % (20, t, 40, l, d))


def print_unseens(unseen):
	'''Print unseen job IDs and Titles to conclude the search'''
	print('\n')
	print(colored("\t%-*s" %
		(62, 'UNSEEN POSITIONS'), 'yellow'))

	print(colored("\t%-*s  %-*s  %s" %
	(62, 'DEPARTMENT', 60, 'JOB TITLE', 'LOCATION'), 'green'))
	for job in unseen:
		print("\t%-*s  %-*s  %s" % (62, job['department'], 60, job['title'], job['location']))
		#print('\t', , '\t', job['title'])
	print('\n')

def write_to_csv(list_of_dicts, file_name):
	'''jobs details to CSV'''
	keys = list_of_dicts[0].keys()
	with open(file_name, 'w', newline='') as output_file:
		dict_writer = csv.DictWriter(output_file, keys)
		dict_writer.writeheader()
		dict_writer.writerows(list_of_dicts)

def append_csv(list_of_dicts, file_name):
	'''jobs details to CSV'''
	with open(file_name, 'r', newline='') as f:
		prev = [{k: v for k, v in row.items()}
				for row in csv.DictReader(f, skipinitialspace=True)]
	new = [d for d in list_of_dicts if d not in prev]
	keys = list_of_dicts[0].keys()
	with open(file_name, 'a', newline='') as output_file:
		dict_writer = csv.DictWriter(output_file, keys)
		dict_writer.writerows(new)

def read_from_csv(file_name):
	'''jobs details from CSV'''
	with open(file_name, 'r', newline='') as f:
		a = [{k: v for k, v in row.items()}
			for row in csv.DictReader(f, skipinitialspace=True)]
	return a

def ProBar(iteration, total, prefix = 'Progress:', s = '', decimals = 1, length = 50, fill = '█'):
    """
    Call in a loop to create terminal progress bar
    @params:
        iteration   - Required  : current iteration (Int)
        total       - Required  : total iterations (Int)
        prefix      - Optional  : prefix string (Str)
        suffix      - Optional  : suffix string (Str)
        decimals    - Optional  : positive number of decimals in percent complete (Int)
        length      - Optional  : character length of bar (Int)
        fill        - Optional  : bar fill character (Str)
    """
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filledLength = int(length * iteration // total)
    bar = fill * filledLength + '-' * (length - filledLength)
    print('\r%s |%s| %s%% %s' % (prefix, bar, percent, s), end = '\r')
    # Print New Line on Complete
    if iteration == total:
        print('\r%s |%s| %s%% %s' % (prefix, bar, percent, ''), end = '\r')
        print()

def setTerminal():
	system("title "+"SpaceX Career Search")
	cmd = 'mode 200,40'
	os.system(cmd)


class colors:
    '''Colors class:reset all colors with colors.reset; two
    sub classes fg for foreground
    and bg for background; use as colors.subclass.colorname.
    i.e. colors.fg.red or colors.bg.greenalso, the generic bold, disable,
    underline, reverse, strike through,
    and invisible work with the main class i.e. colors.bold'''
    reset='\033[0m'
    bold='\033[01m'
    disable='\033[02m'
    underline='\033[04m'
    reverse='\033[07m'
    strikethrough='\033[09m'
    invisible='\033[08m'
    class fg:
        black='\033[30m'
        red='\033[31m'
        green='\033[32m'
        orange='\033[33m'
        blue='\033[34m'
        purple='\033[35m'
        cyan='\033[36m'
        lightgrey='\033[37m'
        darkgrey='\033[90m'
        lightred='\033[91m'
        lightgreen='\033[92m'
        yellow='\033[93m'
        lightblue='\033[94m'
        pink='\033[95m'
        lightcyan='\033[96m'
    class bg:
        black='\033[40m'
        red='\033[41m'
        green='\033[42m'
        orange='\033[43m'
        blue='\033[44m'
        purple='\033[45m'
        cyan='\033[46m'
        lightgrey='\033[47m'
