import re
# import openai
#
# def get_api_response(content: str, max_tokens=None):
#
#     response = openai.ChatCompletion.create(
#         model='gpt-3.5-turbo',
#         messages=[{
#             'role': 'system',
#             'content': '你是一个富有创造力且文笔极佳的小说家。'
#         }, {
#             'role': 'user',
#             'content': content,
#         }],
#         temperature=0.5,
#         max_tokens=max_tokens
#     )
#
#     return response['choices'][0]['message']['content']


def get_content_between_a_b(a, b, text):
    match = re.search(f"{a}(.*?){b}", text, re.DOTALL)
    if match:
        return match.group(1).strip().lstrip(":").lstrip("：")
    else:
        return ""


def get_init(init_text=None,text=None,response_file=None):
    """
    init_text: if the title, outline, and the first 3 paragraphs are given in a .txt file, directly read
    text: if no .txt file is given, use init prompt to generate
    """
    if not init_text:
        print("\ncall yiyan ing...")
        response = get_api_response_yiyan(text)
        print(response)

        if response_file:
            with open(response_file, 'a', encoding='utf-8') as f:
                f.write(f"Init output here:\n{response}\n\n")
    else:
        with open(init_text,'r',encoding='utf-8') as f:
            response = f.read()
        f.close()
    paragraphs = {
        "name":"",
        "Outline":"",
        "Paragraph 1":"",
        "Paragraph 2":"",
        "Paragraph 3":"",
        "Summary": "",
        "Instruction 1":"",
        "Instruction 2":"",
        "Instruction 3":""
    }
    paragraphs['name'] = get_content_between_a_b('Name:','Outline',response)

    paragraphs['Paragraph 1'] = get_content_between_a_b('Paragraph 1:','Paragraph 2:',response)
    paragraphs['Paragraph 2'] = get_content_between_a_b('Paragraph 2:','Paragraph 3:',response)
    paragraphs['Paragraph 3'] = get_content_between_a_b('Paragraph 3:','Summary',response)
    paragraphs['Summary'] = get_content_between_a_b('Summary:','Instruction 1',response)
    paragraphs['Instruction 1'] = get_content_between_a_b('Instruction 1:','Instruction 2',response)
    paragraphs['Instruction 2'] = get_content_between_a_b('Instruction 2:','Instruction 3',response)
    lines = response.splitlines()
    # content of Instruction 3 may be in the same line with I3 or in the next line
    if lines[-1] != '\n' and lines[-1].startswith('Instruction 3'):
        paragraphs['Instruction 3'] = lines[-1][len("Instruction 3:"):]
    elif lines[-1] != '\n':
        paragraphs['Instruction 3'] = lines[-1]
    # Sometimes it gives Chapter outline, sometimes it doesn't
    for line in lines:
        if line.startswith('Chapter'):
            paragraphs['Outline'] = get_content_between_a_b('Outline:','Chapter',response)
            break
    if paragraphs['Outline'] == '':
        paragraphs['Outline'] = get_content_between_a_b('Outline:','Paragraph',response)


    return paragraphs

def get_chatgpt_response(model,prompt):
    response = ""
    for data in model.ask(prompt):
        response = data["message"]
    model.delete_conversation(model.conversation_id)
    model.reset_chat()
    return response


def parse_instructions(instructions):
    output = ""
    for i in range(len(instructions)):
        output += f"{i+1}. {instructions[i]}\n"
    return output


import random
import time
from tqdm import tqdm
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import json
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
'''
input://textarea[@class="ant-input wBs12eIN"]
send: //span[@class="pa6BxUpp"]
open: //span[@class="MO979HM2"]
close://span[@class="KtNWFhXf"]/span[2]
del: //button[@class="ant-btn ant-btn-primary ant-btn-sm"]
output:  //div[@class="SZiJRLGn G4lAynef"]
'''
class YiYanSpider(object):
    def __init__(self, outfile="result.json"):
        self.url = "https://yiyan.baidu.com/"
        self.outfile = outfile
        self._init_driver()

    def _init_driver(self):
        chrome_options = Options()
        chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
        self.driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()),options=chrome_options)
        self.rand_sleep()
        # self.driver.get(self.url)
        msg = input("请登录https://yiyan.baidu.com/后，按'ok'确认,或'quit'退出：")
        while msg != "ok":
            msg = input("请登录https://yiyan.baidu.com/后，按'ok'确认,或'quit'退出：")
            if msg=="quit":
                break

    def rand_sleep(self,max_time=1):
        time.sleep(random.uniform(0,max_time))

    def open_new_win(self):
        new_win = self.driver.find_element(by=By.XPATH, value='''//span[@class="MO979HM2"]''')
        new_win.click()

    def del_top_win(self):
        top_win = self.driver.find_elements(by=By.XPATH, value='''//span[@class="KtNWFhXf"]/span[2]''')[0]
        top_win.click()
        time.sleep(1)
        del_btn = self.driver.find_element(by=By.XPATH, value='''//button[@class="ant-btn ant-btn-primary ant-btn-sm"]''')
        del_btn.click()

    def ask(self, query):
        input_area = self.driver.find_element(by=By.XPATH, value='''//textarea[@class="ant-input wBs12eIN"]''')
        input_area.send_keys(query)
        time.sleep(1)
        self.send()

    def get_answer(self):
        final_text = ""
        try:
            time.sleep(5)
            last_text = "-1"
            cur_text = "-2"
            while last_text!=cur_text:
                time.sleep(1)
                last_text = cur_text
                try:
                    cur_text = self.driver.find_element(by=By.XPATH, value='''//div[@class="SZiJRLGn G4lAynef"]''').text
                except:
                    break
            final_text = cur_text
        except:
            pass
        return final_text

    def send(self):
        click_btn = self.driver.find_element(by=By.XPATH, value='''//span[@class="pa6BxUpp"]''')
        click_btn.click()


    def run(self, query = ""):
        query = query.replace("\n","")
        self.rand_sleep(2)
        self.open_new_win()
        self.ask(query)
        answer = self.get_answer()
        self.rand_sleep(1)
        # 删除对话窗口
        # self.del_top_win()

        res = {"query": query, "answer": answer}
        return res

yiyan = YiYanSpider()
def get_api_response_yiyan(content: str, max_tokens=None):
    response = yiyan.run(query=content)
    return response["answer"]