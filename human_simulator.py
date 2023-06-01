
from utils import get_content_between_a_b, parse_instructions,get_api_response_yiyan

class Human:

    def __init__(self, input, memory, embedder):
        self.input = input
        if memory:
            self.memory = memory
        else:
            self.memory = self.input['output_memory']
        self.embedder = embedder
        self.output = {}


    def prepare_input(self):
        previous_paragraph = self.input["input_paragraph"]
        writer_new_paragraph = self.input["output_paragraph"]
        memory = self.input["output_memory"]
        user_edited_plan = self.input["output_instruction"]

        input_text = f"""
    现在想象一下，你是一个小说家，在YiYan的帮助下写一本中文小说。你会得到一个先前写好的段落（由你写），和一个由你的YiYan助手写的段落，一个YiYan助手维护的主要故事情节的摘要，以及一个YiYan助手提出的下一步写什么的计划。
    我需要你来写：
    1. Extended Paragraph： 将YiYan助手写的新段落延长到您的YiYan助手写的段落长度的两倍。
    2. Selected Plan： 复制您的YiYan助手提出的计划。
    3. Selected Plan： 将选定的计划修订为下一段的纲要。
    
    以前写的段落： 
    {previous_paragraph}

    由你的YiYan助手维护的主要故事情节的摘要：
    {memory}

    您的YiYan助手写的新段落：
    {writer_new_paragraph}

    您的YiYan助理提出的下一步写作计划：
    {user_edited_plan}

    现在开始写，严格按照下面的输出格式来组织你的输出，所有输出仍然保持是中文：
    
    Extended Paragraph：
    <string of output paragraph>, 大约40-50个句话.

    Selected Plan：
    <copy the plan here>

    Selected Plan：
    <string of revised plan>,保持简短，大约5-7句话。

    非常重要：
    记住，你是在写一本小说。像小说家一样写作，在写下一段的计划时不要走得太快。在选择和扩展计划时，要考虑计划如何对普通读者具有吸引力。记住要遵循长度限制! 记住，这一章将包含10多段，而小说将包含100多章。而下一段将是第二章的第二段。你需要为未来的故事留出空间。

    """
        return input_text
    
    def parse_plan(self,response):
        plan = get_content_between_a_b('Selected Plan:','Reason',response)
        return plan


    def select_plan(self,response_file):
        
        previous_paragraph = self.input["input_paragraph"]
        writer_new_paragraph = self.input["output_paragraph"]
        memory = self.input["output_memory"]
        previous_plans = self.input["output_instruction"]
        prompt = f"""
    现在想象一下，你是一个帮助小说家做决定的助手。你将得到一个以前写的段落和一个由YiYan写作助理写的段落，一个由YiYan助理保持的主要故事情节的摘要，以及接下来要写的三个不同的可能计划。
    我需要你
    选择由YiYan助手提出的最有趣和最合适的计划。

    以前写的段落：
    {previous_paragraph}

    由你的ChatGPT助手维护的主要故事情节的摘要：
    {memory}

    您的ChatGPT助理写的新段落：
    {writer_new_paragraph}

    由你的ChatGPT助理提出的下一步写什么的三个计划：
    {parse_instructions(previous_plans)}

    现在开始选择，严格按照下面的输出格式来组织你的输出：
      
    Selected Plan: 
    <将选定的计划复制到这里>

    Reason:
    <解释你为什么选择该计划>
    """
        print(prompt+'\n'+'\n')

        response = get_api_response_yiyan(prompt)

        plan = self.parse_plan(response)
        while plan == None:
            response = get_api_response_yiyan(prompt)
            plan= self.parse_plan(response)

        if response_file:
            with open(response_file, 'a', encoding='utf-8') as f:
                f.write(f"Selected plan here:\n{response}\n\n")

        return plan
        
    def parse_output(self, text):
        try:
            if text.splitlines()[0].startswith('Extended Paragraph'):
                new_paragraph = get_content_between_a_b(
                    'Extended Paragraph:', 'Selected Plan', text)
            else:
                new_paragraph = text.splitlines()[0]

            lines = text.splitlines()
            if lines[-1] != '\n' and lines[-1].startswith('Revised Plan:'):
                revised_plan = lines[-1][len("Revised Plan:"):]
            elif lines[-1] != '\n':
                revised_plan = lines[-1]

            output = {
                "output_paragraph": new_paragraph,
                # "selected_plan": selected_plan,
                "output_instruction": revised_plan,
                # "memory":self.input["output_memory"]
            }

            return output
        except:
            return None

    def step(self, response_file=None):

        prompt = self.prepare_input()
        print(prompt+'\n'+'\n')

        response = get_api_response_yiyan(prompt)
        self.output = self.parse_output(response)
        while self.output == None:
            response = get_api_response_yiyan(prompt)
            self.output = self.parse_output(response)
        if response_file:
            with open(response_file, 'a', encoding='utf-8') as f:
                f.write(f"Human's output here:\n{response}\n\n")
