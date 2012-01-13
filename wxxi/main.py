import urllib2
from BeautifulSoup import BeautifulSoup # For processing HTML
import csv
import math
import os
import re

baseurl = """
http://patft.uspto.gov/netacgi/nph-Parser?Sect1=PTO2&Sect2=HITOFF&u=%2Fnetahtml%2FPTO%2Fsearch-adv.htm&r={0}&f=S&l=50&d=PTXT&RS=%28%28AN%2Fkodak+AND+IC%2Frochester%29+AND+IS%2Fny%29&Query=an%2Fkodak+and+ic%2Frochester+and+is%2Fny&TD=11934&Srch1=%28%28kodak.ASNM.+AND+rochester.INCI.%29+AND+%28ny.INST.%29%29&StartAt=Jump+To&StartAt=Jump+To&StartNum={1}"""

base = "http://patft.uspto.gov"

p_url = """http://patft.uspto.gov/netacgi/nph-Parser?Sect1=PTO1&Sect2=HITOFF&d=PALL&p=1&u=%2Fnetahtml%2FPTO%2Fsrchnum.htm&r=1&f=G&l=50&s1={0}.PN.&OS=PN/{0}&RS=PN/{0}"""

nuke_lines = (lambda w: ' '.join([x.strip() for x in w.strip().splitlines()]))

def scrape_patent(csv_out, p_id):
    url = p_url.format(p_id)
    page = urllib2.urlopen(url)

    soup = BeautifulSoup(page)

    print "Patent #"+p_id+':'

    patent_name = nuke_lines(soup.html.body.findAll('font', {"size":"+1"})[0].string)

    info_tables = soup.html.body.findAll('table', {"width":"100%"})[1:]
    
    patent_id_table = info_tables[0].findAll('tr')
    patent_id =  patent_id_table[0].findAll('td')[1].contents[-1].strip()

    issue_date = patent_id_table[1].findAll('td')[1].b.string.strip()
    
    patent_base_info_table = info_tables[1].findAll('tr')

    inventors = ""
    assignee = ""
    appl_id = ""
    appl_date = ""

    for row in patent_base_info_table:
        cols = row.findAll('td')
        try:
            if u"Inventors" in cols[0].string:
                inventors_td = cols[1]
                inventors_lst = [nuke_lines(x.string.strip(',')).replace(";", ',') for x in inventors_td.findAll('b')]
                inventors = "; ".join(inventors_lst)
            if u"Filed" in cols[0].string:
                appl_date = nuke_lines(cols[1].b.string)
            if u"Appl. No" in cols[0].string:
                appl_id = nuke_lines(cols[1].b.string)
            if u"Assignee" in cols[0].string:
                assignee =  cols[1].b.string.strip() + " " + nuke_lines(cols[1].contents[2])
        except TypeError:
            pass # We don't care, its usually a 'Notice'


    patent_class_info_table = info_tables[2].findAll('tr')
    if not len(info_tables[2].findAll(text=re.compile("Current U.S. Class"))):
        patent_class_info_table = info_tables[3].findAll('tr')

    patent_classes = ""
    b = ""
    for row in patent_class_info_table:
        cols = row.findAll('td')
        try:
            if u"Current U.S. Class" in cols[0].b.string:
                for a in cols[1].findAll('b'):
                    b = b + ";" + a.string
                for a in cols[1].contents:
                    try:
                        b = b + ";" + a.string
                    except:
                        pass
        
                patent_classes = "; ".join(list(set([x.strip() for x in filter((lambda x: len(x.strip()) is not 0), b.split(';'))])))
            
        except AttributeError:
            pass
        except TypeError:
            pass

    if not len(patent_classes.strip()):
        raise Exception, "Missing patent classes."

    print "\tName:", patent_name
    print "\tIssue Date:", issue_date
    print "\tAssignee:", assignee
    print "\tFile Date:", appl_date
    print "\tApplication ID:", appl_id
    print "\tInventors: ", inventors
    print "\tPatent Classes: ", patent_classes
    print

    csv_out.writerow([patent_id, patent_name, issue_date, appl_date, appl_id, inventors, assignee, patent_classes, url])


def index_search_page():
    with open("index.csv", 'wb') as csv_index_out_file:
        csv_out = csv.writer(csv_index_out_file, quoting=csv.QUOTE_MINIMAL)

        p_count = 0
        patent_id_list = []

        # TODO: Fix this damn dirty ape hack
        for i in range(0, int(math.ceil(11935/50.0))):
        #for i in range(0, 1):
            url = baseurl.format(0, (i*50)+1) # r is result (0 is result page)

            page = urllib2.urlopen(url)
            soup = BeautifulSoup(page)

            patent_table = soup.html.body.findAll('table')[1]

            patent_rows = patent_table.findAll('tr')[1:] # Skip first row (header)
            
            for row in patent_rows:
                row_td = row.findAll('td')
                row_id = row_td[0].string
                patent_url = row_td[1].a['href']
                patent_id = row_td[1].a.string.strip()
                patent_id_list.append(patent_id)
                patent_title = row_td[3].a.string
                patent_title = nuke_lines(patent_title)
                csv_out.writerow([row_id.strip(), patent_id.strip(), patent_title])
                

            print "Logged page {0}, {1} patents indexed.".format(i, len(patent_rows))
            p_count = p_count + len(patent_rows)

        print "Indexing completed, {0} patents indexed.".format(p_count)
        return patent_id_list

if __name__ == "__main__":


    if os.path.exists('patent_data.csv'):
        mode = "ab"
        # get the last record scraped
        p_data_file = open('patent_data.csv', 'rb')
        p_data = csv.reader(p_data_file, quoting=csv.QUOTE_MINIMAL)
        last_id = None
        for rec in p_data:
            last_id = str(rec[0])
        p_data_file.close()

        # Open the Index and get the list of patents
        p_index_file = open('index.csv', 'rb')
        p_index = csv.reader(p_index_file, quoting=csv.QUOTE_MINIMAL)
        patent_id_list = []
        for rec in p_index:
            patent_id_list.append(str(rec[1]))
        p_index_file.close()

        i = patent_id_list.index(last_id)
        patent_id_list = patent_id_list[i+1:]

    else:
        mode = "wb"
        patent_id_list = index_search_page()        

    with open("patent_data.csv", mode) as csv_out_file:
        csv_out = csv.writer(csv_out_file, quoting=csv.QUOTE_MINIMAL)
        if mode is 'wb':
            csv_out.writerow(['patent_id','patent_name', 'issue_date', 'appl_date', 'appl_id', 'inventors', 'assignee','patent_classes', 'url'])

        for p_id in patent_id_list:
            scrape_patent(csv_out, p_id)
