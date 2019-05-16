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
from datetime import date

def spacex_job_search_url():
	'''create the amazon job search url'''
	# Specify the URL
	url = 'http://www.spacex.com/careers/list'
#	url += '?field_job_category_tid[]=426'
#	url += '&field_job_category_tid[]=886'
#	url += '&type[]=20'
#	url += '&location[]=54'
#	url += '&location[]=906'
#	url = url.replace('[]', '%5B%5D')
	return url

def get_search_results(driver):
	'''Retrieve details about amazon job search and .'''
	print('\nScrapping Search Results Page')
	# Get HTML
	soup = BeautifulSoup(driver.page_source, 'lxml')
	# List to store Jobs
	jobs = []
	# Position Details from Beutiful Soup
	results_even = soup.find_all("tr", {"class": "odd"})
	results_odd = soup.find_all("tr", {"class": "even"})
	results = results_even + results_odd
	for x in range(0, len(results)):
		job = {}
		# Position
		job['title'] = results[x].td.a.contents[0]
		# URL
		url_end = results[x].td.a.get('href').strip()
		#job['url'] = 'http://www.spacex.com' + url_end
		job['url'] = url_end
		# ID
		job['id'] = job['url'][-10:]
		# Location
		location = results[x].find_all('td')[1].div.contents[0].strip()
		job['country'] = location
		# Excel URL
		job['xl url'] = '=HYPERLINK("' + job['url'] + '", "View Online")'
		job['img_name'] = 'spacex_job_images/' + job['id'] + '.png'
		pathname = os.path.dirname(sys.argv[0])
		folder_path = os.path.abspath(pathname)
		full_path = folder_path + '\\' + job['img_name']
		job['xl img'] = '=HYPERLINK("' + full_path + '", "Job Img")'
		job['date'] = str(date.today())
		jobs.append(job)
	return jobs

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
	print('- ', len(results), ' results')
	print('- ', len(unseen), ' unseen')

def screenshot_positions(driver, unseen):
	'''Screenshot Amazon Job Positions'''
	print('\nScreenshotting Unseen Positions')
	l = len(unseen)
	for x in range(0, l):
		# Navigate and Get HTML
		driver.get(unseen[x]['url'])
		# Application Link
		app = "" #driver.find_element_by_id('apply_button')
		unseen[x]['apply_url'] = "www.google.com" #app.get_attribute('href')
		# Screenshot
		element = driver.find_element_by_id('content')
		element_png = element.screenshot_as_png
		with open(unseen[x]['img_name'], "wb") as file:
			file.write(element_png)
		ProBar(x + 1, l, s = 'Complete\t' + str(unseen[x]['id']))

def send_emails(unseen):
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

def send_preview_emails(unseen):
	'''Send an Email with job details and screenshot of listing.'''
	print('\nSending Unseen Position Emails')
	# Variables
	FROM_EMAIL = 'aaronjameslutz@gmail.com' #'aaronlutz@yahoo.com'
	PASSWORD = 'PacificNorthWEST' #'@@ronlu+z'
	TO_EMAIL = 'aaronjameslutz@gmail.com'

	# Log into Email Server
	#server = smtplib.SMTP(host='smtp.mail.yahoo.com', port=587)
	server = smtplib.SMTP(host='smtp.gmail.com', port=587)
	server.ehlo()
	server.starttls()
	server.ehlo()
	server.login(FROM_EMAIL, PASSWORD)

	min_ = 0
	max_ = len(unseen)
	for x in range(0, len(unseen), 10):
		# Get Subsection of List
		if x+10 > max_:
			list_max = max_
		else:
			list_max = x+10
		jobs = [unseen[x] for x in range(x,list_max)]

		# Email Details
		msgRoot = MIMEMultipart('related')
		msgRoot['From'] = FROM_EMAIL
		msgRoot['To'] = TO_EMAIL
		_title = unseen[x]['title']
		_id = unseen[x]['id']
		msgRoot['Subject'] = 'Amazon Job: 10 unseen postings'

		# Multiple Images and Links in Body
		html = ''
		for j in range(0, len(jobs)):
			# Prepare Message HTML
			preffix = 'Posted: ' + unseen[x+j]['posted']
			job_url = jobs[x+j]['url']
			app_url = jobs[x+j]['apply_url']
			html += """
				<p>""" + preffix + """ &nbsp;
					<a href=""" + job_url + """>View Position</a> &nbsp;
					<a href=""" + app_url + """>Apply</a><br>
					<img src="cid:image""" + str(x+j+1) + """ width=924>
				</p>
			"""
		msgHtml = MIMEText(html, 'html')
		msgRoot.attach(msgHtml)
		for j in range(0, len(jobs)):
			# Prepare Image
			img_name = unseen[x+j]['list_img']
			img = open(img_name, 'rb').read()
			msgImg = MIMEImage(img, 'png')
			msgImg.add_header('Content-ID', '<image' + str(x+j+1) + '>')
			msgImg.add_header('Content-Disposition', 'inline', filename=img_name)
			msgRoot.attach(msgImg)

		# Attach MIME types to Message Root.


		# Send the message via local SMTP server.
		server.send_message(msgRoot)
		ProBar(x + 10, len(unseen), s = 'Complete\t' + str(unseen[x]['id']))
	# Quit Server after Emails Sent
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

def print_unseens(unseen):
	'''Print unseen job IDs and Titles to conclude the search'''
	print('\nUnseen Positions:')
	for job in unseen:
		print('\t', job['id'], '\t', job['title'])
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

def run_new_search(fresh_start=False, to_page=0):
	'''Get the newest jobs from a amazon job search.'''
	file_names = {'ids': 'csv_logs\\spacex_job_ids.csv',
				  'pos': 'csv_logs\\spacex_positions.csv',
				  'unseen': 'csv_logs\\spacex_unseen_job_ids.csv'}

	msg  = '\n█████████████████████████'
	msg += '\n██   SpaceX Job Hunt   ██'
	msg += '\n█████████████████████████\n'
	print(msg)


	# Delete files to erase record of seen files
	if fresh_start:
		delete_files(file_names)

	# Headless Driver
	print('Starting Up')
	print('- creating headless firefox driver')
	options = Options()
	options.add_argument("--headless")
	driver_path = r"C:\Users\aaron\Documents\python_work\going_headless\geckodriver.exe"
	driver = webdriver.Firefox(executable_path=driver_path, firefox_options=options)
	# URL for Search
	print('- navigating to initial job search')
	url = spacex_job_search_url()
	driver.get(url)
	# All Search Results
	search_results = get_search_results(driver)
	# Unseen Results
	unseen = []
	get_unseen_results(file_names, search_results, unseen)
	# Screenshot Unseen Positions
	if len(unseen) != 0:
		screenshot_positions(driver, unseen)
	else:
		msg  = '\n░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░'
		msg += '\n░░ All Positions Previously Viewed ░░'
		msg += '\n░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░\n'
		print(msg)
	driver.quit()
	# Email Unseen Position Screenshots
	if len(unseen) != 0:
		send_emails(unseen)
		# Printed Unseen Summary
		print_unseens(unseen)
