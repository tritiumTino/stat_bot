# Python 3.7
# -*- coding: utf_8 -*-

from PyQt5 import QtWidgets, QtGui
import sys
from stat_bot_gui import Ui_mainWindow
import re
from datetime import datetime, timedelta
from selenium import webdriver


def convert_time(forum_time):
    """функция принимает дату последнего поста и переводит ее в datetime формат"""
    forum_time = forum_time.split()
    if 'Сегодня' in forum_time:
        forum_time[0] = f'{datetime.now().year} {datetime.now().month} {datetime.now().day}'
    elif 'Вчера' in forum_time:
        new_date = datetime.now() - timedelta(days=1)
        forum_time[0] = f'{new_date.year} {new_date.month} {new_date.day}'
    forum_time = re.split(r'[-:\s]', ' '.join(forum_time))
    forum_time = (map(int, forum_time))
    return datetime(*forum_time)


class StatBot:
    def __init__(self, user_start_time, user_login=None, user_password=None):
        self.options = webdriver.ChromeOptions()
        self.options.add_argument('--blink-settings=imagesEnabled=false')
        self.options.add_argument("--headless")
        self.executable_path = './driver/chromedriver.exe'
        self.section_links = ['http://freshair.rusff.me/viewforum.php?id=20',
                              'http://freshair.rusff.me/viewforum.php?id=18']

        self.login = user_login
        self.password = user_password
        self.time_start = user_start_time

        self.final_statistic = {}
        self.names, self.all_episodes, self.users_id, self.posts_length = [], [], [], []
        self.driver = webdriver.Chrome(options=self.options, executable_path=self.executable_path)

        if self.check_user_info() is True:
            self.get_forum_sections()
            self.create_ep_list()
            self.create_stat_data()
            self.get_names()
            self.get_final_stat_dict()
            self.get_final_stat_list()
            self.get_stat_info()
        else:
            with open("final.stat.txt", "w", encoding='utf-8') as f_obj:
                f_obj.write('Некорректные данные профиля. Попробуйте еще раз')
        self.driver.quit()

    def site_login(self):
        self.driver.get('http://freshair.rusff.me/login.php')
        self.driver.find_element_by_name('req_username').send_keys(self.login)
        self.driver.find_element_by_name('req_password').send_keys(self.password)
        self.driver.find_element_by_name('login').click()

    def check_user_info(self):
        # проверяем ввел ли пользователь корректные данные
        if self.login == '' or self.password == '':
            return False
        self.site_login()
        verification = self.driver.find_element_by_css_selector('div.section p.container span.item1').text
        if verification == 'Привет, Гость!':
            return False
        return True

    def get_forum_sections(self):
        # формируем список игровых разделов
        for i in self.driver.find_elements_by_css_selector('#pun-category4 h3 > a'):
            link = i.get_attribute('href')
            if not int(link[-1]) == 6:
                self.section_links.append(link)

    def create_ep_list(self):
        # добавляем в список эпизодов ссылки эпизодов, последнее сообщение которых попадает в диапазон
        for link in self.section_links:
            self.driver.get(link)
            for i in self.driver.find_elements_by_css_selector('td.tcr > a')[1:]:
                text = i.get_attribute('innerText')
                if convert_time(text) >= self.time_start:
                    self.all_episodes.append(i.get_attribute('href').split('#')[0])

    def create_stat_data(self):
        # собираем id и длину постов за отчетный период
        for link in self.all_episodes:
            self.driver.get(link + '&p=-1')
            # считаем количество постов по условию
            for post in self.driver.find_elements_by_css_selector('.topic .post:not(.topicpost)'):
                if int(post.get_attribute('data-posted')) >= int(self.time_start.toTime_t()):
                    self.users_id.append(post.get_attribute('data-user-id'))
                    self.posts_length.append(int(post.find_element_by_css_selector('#countreal').get_attribute('innerHTML')))

    def get_names(self):
        # создаем список ников
        self.driver.get('http://freshair.rusff.me/userlist.php')
        for u_id in self.users_id:
            for href in self.driver.find_elements_by_css_selector('div.usertable span.usersname > a'):
                url = href.get_attribute('href')
                if url == 'http://freshair.rusff.me/profile.php?id=' + u_id:
                    self.names.append(href.get_attribute('innerText'))

    def get_final_stat_dict(self):
        # формируем словарь со статистикой
        for name, length in zip(self.names, self.posts_length):
            self.final_statistic[name] = self.final_statistic.get(name, 0) + length

    def get_final_stat_list(self):
        # изменяем формат для вывода
        self.final_statistic_list = list(self.final_statistic.items())
        self.final_statistic_list.sort(key=lambda i: i[1])
        return '\n'.join(" : ".join(map(str, line)) for line in reversed(self.final_statistic_list))

    def get_stat_info(self):
        # записываем итог в файл
        with open("final.stat.txt", "w", encoding='utf-8') as f_obj:
            f_obj.writelines(f'Статистика сформирована {datetime.now()}\n')
            f_obj.writelines((self.get_final_stat_list(), '\n'))
            f_obj.write(f'Всего символов: {sum(self.final_statistic.values())}')


class BotWindow(QtWidgets.QMainWindow):
    def __init__(self, *args, **kwargs):
        super(BotWindow, self).__init__(*args, **kwargs)

        self.ui = Ui_mainWindow()
        self.ui.setupUi(self)
        self.user_login = ''
        self.user_password = ''
        self.ui.pushButton_2.clicked.connect(self.set_variables_to_bot)
        self.ui.pushButton.clicked.connect(self.run_bot)

    def set_variables_to_bot(self):
        self.user_login = self.ui.login.text()
        self.user_password = self.ui.password.text()
        self.start_time = self.ui.date.dateTime()
        self.start_time.toPyDateTime()

    def run_bot(self):
        self.bot = StatBot(self.start_time, self.user_login, self.user_password)
        self.close()


if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    # иконка приложения
    ico = QtGui.QIcon('./icons/icon.png')
    app.setWindowIcon(ico)
    app.processEvents()
    application = BotWindow()

    # указываем заголовок окна
    application.setWindowTitle("StaT-Bot")
    # задаем минимальный размер окна, до которого его можно ужимать
    application.setMaximumSize(800, 600)
    application.show()
    sys.exit(app.exec())
