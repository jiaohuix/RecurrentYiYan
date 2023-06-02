from utils import get_content_between_a_b, get_api_response_yiyan
import torch

import random

from sentence_transformers import  util


class RecurrentYiYan:

    def __init__(self, input, short_memory, long_memory, memory_index, embedder):
        self.input = input
        self.short_memory = short_memory
        self.long_memory = long_memory
        self.embedder = embedder
        if self.long_memory and not memory_index:
            self.memory_index = self.embedder.encode(
                self.long_memory, convert_to_tensor=True)
        self.output = {}

    def prepare_input(self, new_character_prob=0.1, top_k=2):

        input_paragraph = self.input["output_paragraph"]
        input_instruction = self.input["output_instruction"]

        instruction_embedding = self.embedder.encode(
            input_instruction, convert_to_tensor=True)

        # get the top 3 most similar paragraphs from memory

        memory_scores = util.cos_sim(
            instruction_embedding, self.memory_index)[0]
        top_k_idx = torch.topk(memory_scores, k=top_k)[1]
        top_k_memory = [self.long_memory[idx] for idx in top_k_idx]
        # combine the top 3 paragraphs
        input_long_term_memory = '\n'.join(
                [f"Related Paragraphs {i+1} :" + selected_memory for i, selected_memory in enumerate(top_k_memory)])
        # randomly decide if a new character should be introduced
        if random.random() < new_character_prob:
            new_character_prompt = f"如果它是合理的，你可以在输出段落中引入一个新的字符，并将其添加到记忆中。"
        else:
            new_character_prompt = ""
        print("len Memory", len(self.short_memory))
        print("len Paragraph", len(input_paragraph))
        print("len Instruction", len(input_instruction))
        print("len input_long_term_memory", len(input_long_term_memory))
        input_text = f"""根据输入的素材写小说三部分：
    1. Output Paragraph: 小说的下一段，包含约20个句子，应遵循输入说明。
    2. Output Memory: 更新后的记忆。先删除部分记忆内容并解释，再添加新的记忆并解释，最后写出更的记忆，长度不超过20个句子！
    3. Output Instruction：最后输出3条不同剧情走向的指令，每条指令都是故事的一个可能的有趣的延续，每条指令应该包含大约5个句子，推进剧情走向
    以下是输入的内容：

    Input Memory:  
    {self.short_memory}

    Input Paragraph:
    {input_paragraph}

    Input Instruction:
    {input_instruction}

    Input Related Paragraphs:
    {input_long_term_memory}
    
    严格按照下面输出格式来组织输出，前缀用英文，输出中文：
    Output Paragraph: 
    <输出段落的文本>,大约20句话。

    Output Memory: 
    Rational: <解释如何更新记忆的文本>;
    Updated Memory: <更新的记忆的文本>, 10-20句话

    Output Instruction: 
    Instruction 1: <指令1内容>，大约5句话。
    Instruction 2: <指令2内容>，大约5句话。
    Instruction 3: <指令3内容>，大约5句话。
    
    注意：更新的记忆不超过500字，只存关键信息；写作节奏不易过快，多写具体且有趣的剧情，不要一笔带过。

    {new_character_prompt}
    """
        extra='''
            重要：更新的记忆应该只存储关键信息。更新后的记忆不应该包含超过500个字！
    最后，记住你在写一本小说。像小说家一样写作，在写下一段的输出指令时不要走得太快。记住，这一章将包含10多段，小说将包含100多章。而这仅仅是个开始。只要写出一些接下来会发生的有趣的人员。另外，在写输出说明时，要考虑什么情节能吸引普通读者。

    重要： 
    你应该首先解释哪些输入记忆不再需要及原因，然后解释需要添加到记忆中的内容及原因。之后重写得到新的记忆。
        '''
        return input_text

    def parse_output(self, output):
        try:
            output_paragraph = get_content_between_a_b(
                'Output Paragraph:', 'Output Memory', output)
            output_memory_updated = get_content_between_a_b(
                'Updated Memory:', 'Output Instruction:', output)
            self.short_memory = output_memory_updated
            ins_1 = get_content_between_a_b(
                'Instruction 1:', 'Instruction 2', output)
            ins_2 = get_content_between_a_b(
                'Instruction 2:', 'Instruction 3', output)
            lines = output.splitlines()
            # content of Instruction 3 may be in the same line with I3 or in the next line
            if lines[-1] != '\n' and lines[-1].startswith('Instruction 3'):
                ins_3 = lines[-1][len("Instruction 3:"):]
            elif lines[-1] != '\n':
                ins_3 = lines[-1]

            output_instructions = [ins_1, ins_2, ins_3]
            assert len(output_instructions) == 3

            output = {
                "input_paragraph": self.input["output_paragraph"],
                "output_memory": output_memory_updated,  # feed to human
                "output_paragraph": output_paragraph,
                "output_instruction": [instruction.strip() for instruction in output_instructions]
            }

            return output
        except:
            return None

    def step(self, response_file=None):
        print("YiYan writing novel ...\n")
        prompt = self.prepare_input()

        print(prompt+'\n'+'\n')

        response = get_api_response_yiyan(prompt)

        self.output = self.parse_output(response)
        while self.output == None:
            response = get_api_response_yiyan(prompt)
            self.output = self.parse_output(response)
        if response_file:
            with open(response_file, 'a', encoding='utf-8') as f:
                f.write(f"Writer's output here:\n{response}\n\n")

        self.long_memory.append(self.input["output_paragraph"])
        self.memory_index = self.embedder.encode(
            self.long_memory, convert_to_tensor=True)
