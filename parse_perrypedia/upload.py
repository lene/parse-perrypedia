__author__ = 'Lene Preuss <lene.preuss@gmail.com>'

from typing import List

from lxml import etree
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.webelement import FirefoxWebElement
from selenium.webdriver.support.select import Select

from parse_perrypedia.parse import PerryRhodanPage

UPLOAD_URL = 'https://www.goodreads.com/book/new'
LOGIN_URL = 'https://www.goodreads.com/user/sign_in'


class UploadError(RuntimeError):
    pass


class Uploader:
    def __init__(self, account: str, password: str):
        self.account = account
        self.password = password
        self.driver = self.init_selenium()
        self.uploaded: List[PerryRhodanPage] = []
        self.login()

    @staticmethod
    def init_selenium() -> webdriver.Firefox:
        options = Options()
        options.headless = True
        return webdriver.Firefox(options=options)

    def login(self) -> None:
        self.driver.get(LOGIN_URL)
        print(self.driver.title)
        email_field = self.find_element('//form[@name="sign_in"]//input[@id="user_email"]')
        email_field.send_keys(self.account)
        password_field = self.find_element('//form[@name="sign_in"]//input[@id="user_password"]')
        password_field.send_keys(self.password)
        submit_button = self.find_element(
            '//form[@name="sign_in"]//input[@name="next" and @type="submit"]'
        )
        submit_button.click()
        print(self.driver.title)

    def upload(self, pages: List[PerryRhodanPage]) -> List[PerryRhodanPage]:
        for page in pages:
            if not self.exists_on_goodreads(page):
                try:
                    self.upload_page(page)
                except UploadError as err:
                    print(err)
        return self.uploaded

    def exists_on_goodreads(self, page: PerryRhodanPage) -> bool:
        return False

    def upload_page(self, page: PerryRhodanPage) -> None:
        self.driver.get(UPLOAD_URL)
        print(self.driver.title)
        fieldids_values = {
            'book_title': page.title,
            'book_sort_by_title': page.title,
            'author_name': page.author,
            'book_publisher': page.publisher,
            'book_publication_year': page.publish_date.year,
        }
        for field_id, value in fieldids_values.items():
            if value:
                print(field_id)
                field = self.find_element(f'//form[@name="bookForm"]//input[@id="{field_id}"]')
                field.send_keys(value)
        selectids_values = {
            'book_publication_month': str(page.publish_date.month),
            'book_publication_day': str(page.publish_date.day),
            'book_format': 'ebook',
            'book_language_code': 'ger',
        }
        for select_id, value in selectids_values.items():
            print(select_id)
            select = Select(
                self.find_element(f'//form[@name="bookForm"]//select[@id="{select_id}"]')
            )
            select.select_by_value(value)
        textareaids_values = {
            'book_description_defaulted': page.synopsis,
        }
        for textarea_id, value in textareaids_values.items():
            if value:
                print(textarea_id)
                textarea = self.find_element(f'//form[@name="bookForm"]//textarea[@id="{textarea_id}"]')
                textarea.send_keys(value)
        submit_button = self.find_element(
            '//form[@name="bookForm"]//input[@name="commit" and @type="submit"]'
        )

        self.uploaded.append(page)

    def find_element(self, xpath: str) -> FirefoxWebElement:
        found = self.driver.find_elements_by_xpath(xpath)
        if not found:
            raise UploadError(f"didn't find {xpath}")
        return found[0]
