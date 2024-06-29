"""DO NOT rename this file!"""
import os
import json
import re
import textwrap
import time
from string import Template
import openai
from tqdm import tqdm
import random
import http.client
from string import Template

random.seed(3)

class MyTemplate(Template):
    delimiter = "%"

class Submission:
    """A submission template."""

    def __init__(self, output_file: str):
        self.output_file = output_file
        self.task = "Automated_Theorem_Generation"
        self.phase = "development"
        self.api_key = '***'
        self.base_url = 'api.chatanywhere.cn'
        self.headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}'
        }
        self.prompt = MyTemplate("""
        You are an expert in mathematics, specifically skilled in using the Metamath formal language. Your task is to derive new theorems from the provided axioms and symbols.

        Axioms: 
        %axioms

        Symbols:
        %symbols

        Your output should be structured as follows, detailing the components of a theorem:
        Example:
        {
            "theorem": "mp2",  // This is the label of the new theorem.
            "type": "$p",  // This indicates that the entry is a proposition (a theorem, as opposed to a definition or comment).
            "conclusion": "|- ch",  // This is the statement proved by the theorem.
            "d_vars": "",  // These are the distinct variables used in the theorem, if any.
            "f_hypos": ["wff ph", "wff ps", "wff ch"],  // These are the floating hypotheses of the theorem.
            "e_hypos": ["|- ph", "|- ps", "|- ( ph -> ( ps -> ch ) )"],  // These are the essential hypotheses required for the theorem.
            "proof_steps": "wps wch mp2.2 wph wps wch wi mp2.1 mp2.3 ax-mp ax-mp",  // This is the sequence of proof steps, where each step represents an action in the proof. Steps like 'wps', 'wch' involve pushing variables onto the stack, and steps like 'mp2.2' involve applying a theorem or axiom and then pushing the result onto the stack.
            "references": ["mp2.1", "mp2.2", "mp2.3", "wi", "ax-mp"]  // These are references to axioms or previous theorems used in the proof.
        }

        Note:
        - Each proof step involves either pushing a variable onto the stack or applying a theorem or axiom. The sequence in 'proof_steps' should reflect this orderly process, starting with pushing variables from the stack and applying substitution when encountering theorems. The applied result is then pushed back into the stack.
        - The proof terminates effectively when no more items can be pushed onto the stack.
        - Ensure that the proof operations are performed sequentially as described in 'proof_steps' before arriving at the conclusion.
        - The proof should be verifiable by Metamath.
        - Your reply should only include the new theorem derived, without any additional explanation.

        """)


    def generate(self, prompt):
        """Make a request to the custom API to get the completion. Retry on failure."""
        while True:
            conn = http.client.HTTPSConnection(self.base_url)
            payload = json.dumps({
                'model': 'gpt-3.5-turbo',
                # 'max_tokens': 256,         # 设置最大 token 数
                'messages': [{'role': 'user', 'content': prompt}]
            })
            
            try:
                conn.request("POST", "/v1/chat/completions", payload, self.headers)
                res = conn.getresponse()
                data = res.read()
                if res.status == 200:
                    return json.loads(data)['choices'][0]['message']['content']
                else:
                    print(f"API request failed with status code {res.status}, Response: {data.decode('utf-8')}")
            except Exception as e:
                print(f"Error occurred: {e}. Retrying...")
            finally:
                conn.close()

    def post_process(self, model_output: str):
        """Post-process the model output to extract the theorem and verify the proof."""
        
        try:
            # 使用正则表达式提取 JSON 对象
            json_pattern = re.compile(r'\{.*?\}', re.DOTALL)
            match = json_pattern.search(model_output)
            if not match:
                raise ValueError("No valid JSON found in the input.")
            
            # 提取到的 JSON 字符串
            json_str = match.group(0)
            
            # 解析 JSON 数据
            theorem = json.loads(json_str)
            # print("Successfully parsed JSON")
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON decoding error: {e}")
        except Exception as e:
            raise ValueError(f"Error processing model output: {e}")

        # 定义定理中应包含的必要字段
        keys = ["theorem", "type", "conclusion", "d_vars", "f_hypos", "e_hypos", "proof_steps", "references"]
        
        # 检查解析后的对象是否为字典
        if type(theorem) != dict:
            raise ValueError(f"Output should be a dictionary, got {type(theorem)}.")
        
        # 验证定理中是否包含所有必要字段
        for key in keys:
            if key not in theorem:
                raise ValueError(f"Key {key} not found in the theorem.")

        # 返回解析后的定理
        return theorem

    def run(self, axiom_file: str, symbol_file: str):
            """Run your model on the given input data, and store the 
            predictions into the output file."""

            required_theorems = ['ax-mp', 'wi', 'ax-1', 'df-xor', 'ax-2']
            outputs = []
            
            start = time.time()
            while time.time() - start < 60*19:  # 运行19分钟
                axioms = []
                symbols = []

                # 读取公理文件
                with open(axiom_file, 'r', encoding="utf8") as f:
                    lines = f.readlines()
                    # 首先确保包含指定的五个定理
                    for theorem in required_theorems:
                        for line in lines:
                            axiom = json.loads(line.strip())
                            if axiom['theorem'] == theorem:
                                axioms.append(axiom)
                                break

                    remaining_lines = [line for line in lines if json.loads(line.strip())['theorem'] not in required_theorems]
                    selected_lines = random.sample(remaining_lines, min(len(remaining_lines), 15))
                    for line in selected_lines:
                        axiom = json.loads(line.strip())
                        axioms.append(axiom)

                # 打乱顺序
                random.shuffle(axioms)  
            
                # 读取符号文件
                with open(symbol_file, 'r', encoding="utf8") as f:
                    lines = f.readlines()[:8]

                    for line in lines:
                        symbol = json.loads(line)
                        symbols.append(symbol)
                # print(f'axioms number = {len(axioms)}, symbols = {len(symbols)}')
                # 合并公理、符号和已知定理
                formatted_axioms = "\n".join([json.dumps(ax) for ax in axioms]) 
                formatted_symbols = "\n".join([json.dumps(sym) for sym in symbols])
        
                # 构建prompt
                prompt = self.prompt.safe_substitute(
                    axioms=formatted_axioms,
                    symbols=formatted_symbols,
                    # proven_theorems=formatted_theorems
                )        
                # print(prompt)
                
                model_output = self.generate(prompt)
                # print(model_output)
                try:
                    theorem = self.post_process(model_output)
                except Exception as e:
                    print(f"Error in post-processing: {e}, skip this output.")
                    continue 
                print(theorem)
                outputs.append(json.dumps(theorem))
                if len(outputs)%5==1:
                    print(f'outputs = {len(outputs)}')
            
                if not os.path.exists(self.output_file):
                    os.makedirs(os.path.dirname(self.output_file), exist_ok=True)
                with open(self.output_file, 'w+', encoding='utf8') as f:
                    for output in outputs:
                        f.write(output)
                        f.write('\n')
                        
                                  
                    

# # # Usage example
# submission = Submission(output_file='提交版本/output.json')
# submission.run(axiom_file='ICML/starting_kit/axioms.json', symbol_file='ICML/starting_kit/symbols.json')




