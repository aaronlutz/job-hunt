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


def amazon_job_search_url(search_term='', sort='relevant', start_page=1, seattle=False, country='USA'):
	'''create the amazon job search url'''
	# Replace non text characters from search term
	search_term = urllib.parse.quote_plus(search_term)
	# Specify the URL
	url = 'https://www.amazon.jobs/en/search?'
	# which result page to start on
	url += 'offset=' + str(int((start_page-1)*10))
	url += '&sort=' + sort
	url += '&category=supply-chain-transportation-management'
	if seattle:
		url += '&cities[]=Seattle%2C%20Washington%2C%20USA'
	url += '&distanceType=Mi'
	url += '&radius=24km'
	url += '&base_query=' + search_term
	url += '&city='
	url += '&country=' + country
	return url

def count_result_pages(driver):
	# Get HTML
	soup = BeautifulSoup(driver.page_source, 'lxml')
	page_buttons = driver.find_elements_by_css_selector('button.page-button')
	result_pages = 1
	try:
		result_pages = int(page_buttons[4].text) - 1
	except IndexError:
		result_page = 1
	print('- ' + str(result_pages) + ' pages of results')
	return result_pages

def get_search_results(driver, to_page):
	print('\nScrapping Search Results Pages')
	search_results = []
	for x in range(0, to_page):
		time.sleep(0.25)
		page_results = search_results_page(driver)
		[search_results.append(x) for x in page_results]
		ProBar(x + 1, to_page, s = 'Complete')
		try:
			next_search_results_page(driver)
		except Exception as inst:
			print(inst)
			break
	return search_results

def search_results_page(driver):
	'''Retrieve details about amazon job search and .'''
	# Get HTML
	soup = BeautifulSoup(driver.page_source, 'lxml')
	# List to store Jobs
	jobs = []
	# Position Details from Beutiful Soup
	links = soup.find_all('a')
	for x in range(0, len(links)):
		link_class = links[x].get('class')
		if link_class is not None:
			if link_class[0] == 'job-link':
				job = {}
				# Details
				job['url'] = 'https://www.amazon.jobs'
				job['url'] += links[x].get('href')
				job['title'] = links[x].div.div.div.h2.contents[0]
				loc_and_id = links[x].div.div.div.div.contents[0]
				job['id'] = loc_and_id[-6:]
				job['country'] = loc_and_id[:2]
				job['state'] = loc_and_id[4:6]
				pos_end_city = loc_and_id.find('|') - 1
				job['city'] = loc_and_id[8:pos_end_city]
				posted_text = links[x].div.div.find_all('div')[2]
				posted_text = posted_text.h2.contents[0]
				job['posted'] = posted_text[7:]
				job['list_img'] = 'result_images\\' + job['id'] + '.png'
				# Excel Hyperlink
				pathname = os.path.dirname(sys.argv[0])
				folder_path = os.path.abspath(pathname)

				full_path = folder_path + '\\' + job['list_img']
				job['list_prev'] = '=HYPERLINK("' + full_path + '", "List Img")'

				full_path = folder_path + '\\job_images\\' + job['id'] + '.png'
				job['job_prev'] = '=HYPERLINK("' + full_path + '", "Position Img")'

				jobs.append(job)
	# Preview Screenshot from Selenium
	elements = driver.find_elements_by_css_selector('div.job-tile')
	for e in range(0, len(elements)):
		element_png = elements[e].screenshot_as_png
		with open(jobs[e]['list_img'], "wb") as img_file:
					img_file.write(element_png)
	return jobs

def next_search_results_page(driver):
	'''Advances to the next page of amazon search results.'''
	# Get HTML
	soup = BeautifulSoup(driver.page_source, 'lxml')
	# Next Page Button
	try:
		next_button = driver.find_element_by_css_selector('button.btn.btn-primary.circle.right')
	except:
		error_msg = 'def next_search_results_page() error:\n'
		error_msg += 'Unable to advance to next page.\n'
		error_msg += 'This is likely the last page.'
		raise Exception(error_msg)
	else:
		next_button.click()

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
		write_to_csv(seen_results+unseen, file_names['ids'])
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
		soup = BeautifulSoup(driver.page_source, 'lxml')
		unseen[x]['apply_url'] = soup.find(
								'a', {'id': 'apply-button'}).get('href')
		# Screenshot
		element = driver.find_element_by_tag_name('body')
		element_png = element.screenshot_as_png
		unseen[x]['img_name'] = 'job_images/' + unseen[x]['id'] + '.png'
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
		msgRoot['Subject'] = 'Amazon Job: ' + _title + ' (' + _id + ')'
		# Prepare Message HTML
		preffix = 'Posted: ' + unseen[x]['posted']
		job_url = unseen[x]['url']
		app_url = unseen[x]['apply_url']
		html = """
			<p>""" + preffix + """ &nbsp;
				<a href=""" + job_url + """>View Position</a> &nbsp;
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
			server = smtplib.SMTP(host='smtp.mail.yahoo.com', port=465) #587
			server.ehlo()
			server.starttls()
			server.ehlo()
			server.login(FROM_EMAIL, PASSWORD)
			time.sleep(1)
			#try:
			#	server.connect()
			#except ConnectionRefusedError:
			#	print('\n>>>>> CONNECTION REFUSED BY YAHOO <<<<<')
			#	break
			server.send_message(msgRoot)
		except smtplib.SMTPDataError:
			failed_count += 1
		ProBar(x + 1, len(unseen), s = 'Complete\t' + str(unseen[x]['id']))
	# Quit Server after Emails Sent
	if failed_count != 0:
		print('\t- ', failed_count, ' NOT SENT DUE TO DATA ERRORS')
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

def read_from_csv(file_name):
	'''jobs details from CSV'''
	with open(file_name, 'r', newline='') as f:
		a = [{k: v for k, v in row.items()}
			for row in csv.DictReader(f, skipinitialspace=True)]
	return a

def run_new_search(fresh_start=False, to_page=0):
	'''Get the newest jobs from a amazon job search.'''
	file_names = {'ids': 'csv_logs\\amazon_job_ids.csv',
				  'pos': 'csv_logs\\amazon_positions.csv',
				  'unseen': 'csv_logs\\amazon_unseen_job_ids.csv'}
	# Delete files to erase record of seen files
	if fresh_start:
		msg  = '\n████████████████████████████████████████████'
		msg += '\n██   Amazon Supply Chain Career Search    ██'
		msg += '\n████████████████████████████████████████████\n'
		print(msg)
		delete_files(file_names)
	else:
		msg  = '\n████████████████████████████████████████████'
		msg += '\n██   Amazon Supply Chain Career Search    ██'
		msg += '\n████████████████████████████████████████████\n'
		print(msg)
	# Headless Driver
	print('Starting Up')
	print('- creating headless firefox driver')
	options = Options()
	options.add_argument("--headless")
	driver_path = r"C:\Users\aaron\Documents\python_work\going_headless\geckodriver.exe"
	driver = webdriver.Firefox(executable_path=driver_path, firefox_options=options)
	# URL for Search
	print('- navigating to initial job search')
	url = amazon_job_search_url(sort='recent')
	driver.get(url)
	# All Search Results
	if to_page == 0:
		to_page = count_result_pages(driver)
	search_results = get_search_results(driver, to_page)
	# Unseen Results
	unseen = []
	get_unseen_results(file_names, search_results, unseen)
	# Screenshot Unseen Positions
	if len(unseen) != 0:
		screenshot_positions(driver, unseen)
	else:
		msg  = '\n░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░'
		msg += '\n░░ All Positions Listed Previously Viewed ░░'
		msg += '\n░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░\n'
		print(msg)
	driver.quit()
	# Email Unseen Position Screenshots
	if len(unseen) != 0:
		send_emails(unseen)
		# Printed Unseen Summary
		print_unseens(unseen)
