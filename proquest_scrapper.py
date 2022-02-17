from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from PyPDF2 import PdfFileReader, PdfFileWriter
import os
import time
import timeit
import shutil
import json
import re
import warnings

def log_dauphine(driver, my_id, my_pwd):
    """
    Identifies the user on dauphine's website using my_id and my_pwd.

    Parameters
    ----------
    driver : selenium.webdriver
        A selenium webdriver on a dauphine logging page.
    my_id : string
        User's dauphine's identifier.
    my_pwd : string
        User's dauphine"s password.

    Returns
    -------
    None.

    """
    try:
        driver.find_element(By.ID, "username").send_keys(my_id)
        driver.find_element(By.ID, "password").send_keys(my_pwd)
        driver.find_element(By.XPATH, "//*[@id='fm1']/section[4]/input[4]").click()
    except:
        warnings.warn("Error trying to log into Dauphine.")


def accept_cookies(driver):
    """
    Accepts cookies on proquest's website.

    Parameters
    ----------
    driver : selenium.werbdriver.
        A selenium webdriver asked to accept cookies on proquest's website.

    ReturnsXPATH
    -------
    None.

    """
    # """Accepts cookies on proquest's website"""
    try:
        WebDriverWait(driver,10).until(EC.frame_to_be_available_and_switch_to_it(
            (By.XPATH,'//iframe[@title="TrustArc Cookie Consent Manager"]')))
        WebDriverWait(driver,10).until(EC.element_to_be_clickable(
            (By.XPATH,"//a[@class='call'][text()='Agree and Proceed']"))).click()
        WebDriverWait(driver,5).until(EC.element_to_be_clickable(
            (By.XPATH,"//a[@id='gwt-debug-close_id'][@class='close']"))).click()
        driver.switch_to.default_content()
    except:
        warnings.warn("Error trying to accept cookies.")
        

def setup_driver(url, chromedriver_path, my_id, my_pwd, delay=2):
    """
    Setups a driver by first loging into dauphine's website and then to the url
    accepting cookies.

    Parameters
    ----------
    url : string
        Proquest's url you want to log into.
    chromedriver_path : string
        Path of your chromedriver.
    my_id : string
        User's dauphine's identifier.
    my_pwd : string
        User's dauphine"s password.
    delay : float, optional
        Delay to add in second after logging into dauphine's website and \
            accepting cookies. The default is 2.

    Raises
    ------
    Exception
        DESCRIPTION.

    Returns
    -------
    driver : selenium.webdriver
        Webdriver connected to the given url having both connected into dauphine and accepted cookies.

    """
    dauphine_url = "https://search-proquest-com-s.proxy.bu.dauphine.fr"
    driver = webdriver.Chrome(service = Service(chromedriver_path))
        
    driver.get(dauphine_url)
    log_dauphine(driver, my_id, my_pwd)  
    time.sleep(delay)
    
    if "proquest.com" not in driver.current_url:
        raise Exception(
            "Error trying to reach proquest's website. "\
            "You most likely failed to log into Dauphine.")
        
    accept_cookies(driver)
    time.sleep(delay)
    driver.get(url)
    
    return driver

# https://passeport.dauphine.fr/cas//login?service=https://proxy.bu.dauphine.fr/casReturn/eJwrTk0sSs7QLSjKLyxNLS7RTc7P1S3WA3IrKvWSSvVSEksLMjLzUvXSivQBb5EQWQ


def page_url_recovery(newspapper_url, chromedriver_path, my_id, my_pwd, 
                      delay=2):
    """
    Recovers the url off every article pdf for the given newspapper edition  
    and returns them as well as well as the pages indexes they contain.

    Parameters
    ----------
    newspapper_url : string
        The newspapper url.
    chromedriver_path : string
        Path of your chromedriver.
    my_id : string
        User's dauphine's identifier.
    my_pwd : string
        User's dauphine"s password.
    delay : float, optional
        Delay to add in second after logging into dauphine's website and \
            accepting cookies. The default is 2.

    Returns
    -------
    pdf_list : list of string
        List of pdf's url.
    page_num_list : list of string
        List containing each article's scanned pages under proquest's notation.

    """
    driver = setup_driver(newspapper_url, chromedriver_path, my_id, my_pwd,
                          delay=delay)

    for i in range(10):
        try:
            articles_list = driver.find_element(By.XPATH,
                '//*[@id="contentsZone"]/div/div/div[1]/div[2]/ul')
            break
        except:
            time.sleep(2)
            
            
    articles = articles_list.find_elements(By.TAG_NAME, "li")
    page_list=[]
    
    for article in articles:
        if article.get_attribute("class")=="resultItem ltr":
            try:
                temp_url = article.find_element(By.ID, 
                    "addFlashPageParameterformat_fulltextPDF")
                page_list.append(temp_url.get_attribute("href"))
            except:
                warnings.warn("Error when trying to recover newspapper pages.")
            
    pdf_list = []    
    page_num_list = []
    page_count = 0 
    max_pages = 40 # max number of accesses before the website detects the program as a bot

    driver.get(page_list[0])
    pdf_list.append(driver.find_element(By.XPATH, "//*[@id='embedded-pdf']").get_attribute("src"))
    page_num_list.append(driver.find_element(By.XPATH, '//*[@id="authordiv"]/span[2]').text)

    for page in page_list:   
        if page_count == max_pages:
            driver.close()
            page_count = 0
            driver = setup_driver(newspapper_url, chromedriver_path, 
                                  my_id, my_pwd, delay=delay)
        
        page_count += 1
        driver.get(page)
        pdf_list.append(driver.find_element(By.XPATH, "//*[@id='embedded-pdf']").get_attribute("src"))
        page_num_list.append(driver.find_element(By.XPATH, '//*[@id="authordiv"]/span[2]').text)
        
    driver.close()
    
    return (pdf_list, page_num_list)


def format_num_pages(page_num_list):
    """
    Formats a list of page numbers to a clearer format.

    Parameters
    ----------
    page_num_list : list of string
        List containing each article's scanned pages under proquest's notation.

    Returns
    -------
    res_l : list of list of int
        A list containing a list for each articles, containing the index of each
        scanned page.

    """    
    res_l = []
    aug_factors = {} # Groups special characters together
    # i.e. if we have page indexed by letter N and S they are split in different groups.
    for elem in page_num_list:
        # Step 1: split on ","
        pages = elem.split(",")
        
        final_pages = []
        for elem2 in pages:
            # Step 2: Remove extra characters, if a special character is present
            # we augment its index by 1000
            elem2 = elem2.replace(" ", "")
            aug_factor = 0
            match = re.search("[^0-9|-]", elem2)
            if match is not None:
                string_matched = match.group(0)
                if string_matched not in aug_factors:
                    aug_factors[string_matched] = 1000 * (1 + len(aug_factors))
                elem2 = re.sub("[^0-9|-]", "", elem2)
                aug_factor = aug_factors[string_matched]
                
            # Step 3: If "-" is present we take every element in between
            if "-" in elem2:
                start_page, end_page = elem2.split("-")
                for i in range(int(start_page), int(end_page)+1):
                    final_pages.append(aug_factor + i)
            else:
                final_pages.append(aug_factor + int(elem2))
        
        # We order pages and add them to the result
        final_pages.sort()
        res_l.append(final_pages)
    
    return res_l


def pdf_download(chromedriver_path, pdf_list):
    """
    Downloads every pdf from pdf_list and saves them.

    Parameters
    ----------
    chromedriver_path : string
        Path of your chromedriver.
    pdf_list : list of string
        List of pdf's url.

    Returns
    -------
    None.

    """
    temp_folder = os.getcwd() + "\\temp_folder" 
    download_name = temp_folder + "\\out.pdf"  
    
    options = webdriver.ChromeOptions()
    prefs = {"plugins.always_open_pdf_externally": True, 
             "download.default_directory" : temp_folder,
             "safebrowsing.disable_download_protection" : True,
             "safebrowsing_for_trusted_sources_enabled": False,
             "safebrowsing.enabled": False}
    options.add_experimental_option("prefs", prefs)
    driver = webdriver.Chrome(executable_path=chromedriver_path, options=options)  
    
    if os.path.exists(temp_folder):
        shutil.rmtree(temp_folder)
    
    
    start_time = timeit.default_timer()
    
    for i,pdf_url in enumerate(pdf_list):
        new_name = temp_folder + "\\art" + str(i+1) + ".pdf"      
            
        try:
            driver.get(pdf_url)
        except:
            warnings.warn("Error trying to download article number " \
                          + str(i) + " .")
            
        while not os.path.exists(download_name):
            time.sleep(0.2)
    
        time.sleep(.5) # This is necessary to let chrome scan the file for virus
    
        os.rename(download_name, new_name)
        
    print(f"""Pdfs downloaded in
          {timeit.default_timer()-start_time:.2f} seconds.""")    
    
    driver.close()
    
        
def fuse_pdf(save_path, page_num_list):
    """
    Fuse every pages, removing duplicates and saves the final newspapper pdf.

    Parameters
    ----------
    save_path : string
        Filepath of the pdf you want to save.
    page_num_list : list of string
        List containing each article's scanned pages under proquest's notation.

    Returns
    -------
    None.

    """
    temp_folder = os.getcwd() + "\\temp_folder" 
    temp_folder2 = os.getcwd() + "\\temp_folder2" 
    
    i=0    

    if os.path.exists(temp_folder2):
        shutil.rmtree(temp_folder2)
        
    os.mkdir(temp_folder2)
    
    for filename in sorted(os.listdir(temp_folder), key = lambda x:int(x[3:-4])):
        
        filepath = temp_folder + "\\" + filename
        pdf = PdfFileReader(filepath)
        
        for page in range(pdf.getNumPages()-1):     
            
            try:
                fp_temp = temp_folder2 + "\\" + str(page_num_list[i][page]) + ".pdf"
                
                if not os.path.exists(fp_temp):
                    
                    pdf_writer = PdfFileWriter()
                    pdf_writer.addPage(pdf.getPage(page))
                
                    with open(fp_temp, 'wb') as out:
                        pdf_writer.write(out)
            except: 
                warnings.warn("Error trying to save article number ", i+1, " .")
                    
        i+=1
    
    pdf_writer = PdfFileWriter()
    
    for filename in sorted(os.listdir(temp_folder2), key = lambda x:int(x[:-4])):
        
        filepath = temp_folder2 + "\\" + filename
        pdf = PdfFileReader(filepath)  
        pdf_writer.addPage(pdf.getPage(0))
            
    with open(save_path, 'wb') as out:
        pdf_writer.write(out)
            
    shutil.rmtree(temp_folder)
    shutil.rmtree(temp_folder2)
    
    

def newspapper_download(newspapper_url, chromedriver_path, save_folder, 
                         my_id, my_pwd, delay=2):
    """
    Downloads the newsppaper from newspapper_url and saves it as a pdf.

    Parameters
    ----------
    newspapper_url : string
        The newspapper url.
    chromedriver_path : string
        Path of your chromedriver.
    save_folder : string
        Path of the folder where you want to save the pdf.
    my_id : string
        User's dauphine's identifier.
    my_pwd : string
        User's dauphine"s password.
    delay : float, optional
        Delay to add in second after logging into dauphine's website and \
            accepting cookies. The default is 2.

    Returns
    -------
    None.

    """
    pdf_list,page_num_list = page_url_recovery(
        newspapper_url, chromedriver_path, my_id, my_pwd, delay=delay)
    print("Pdf list successfully recovered.")
    
    newspapper_name = " ".join(page_num_list[0].split()[:-1])[:-1]
    
    page_num_list = [elem.split()[-1][:-1] for elem in page_num_list]
    page_num_list = format_num_pages(page_num_list)
    
    pdf_download(chromedriver_path, pdf_list)    
    
    save_path = save_folder + "\\" + newspapper_name + ".pdf"
    fuse_pdf(save_path, page_num_list)
    
    print("Newspapper successfully saved under name : " + newspapper_name)


if __name__ == "__main__":
    def main_function():
        """Function wrapper to hide the credentials in the variable explorer"""
        
        # Read the user's credentials, you can save/read them however you want
        with open("json_credentials.json") as json_file:
            data = json.load(json_file)    
        my_id,my_pwd = data["my_id"],data["my_password"]
            
        chromedriver_path = "C:\Prog\Python\chromedriver.exe"
        save_folder = "D:\\the_economist"
        newspapper_url = "https://search-proquest-com-s.proxy.bu.dauphine.fr/publication/41716?OpenUrlRefId=info:xri/sid:primo"
        
        # If your internet connection or proquest's website is lagging increase the delay
        delay = 2
        
        newspapper_download(newspapper_url, chromedriver_path, save_folder,
                            my_id, my_pwd, delay=delay)
        
    main_function()

