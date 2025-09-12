import unittest
from asmr_gen_adk.agents.script_agent import script_agent

class TestScriptAgent(unittest.TestCase):

    def test_prompt_generation(self):
        """
        Tests if the instruction for the script_agent is correctly formed.
        """
        instruction = script_agent.instruction
        
        # アサーション: instruction が文字列であること
        self.assertIsInstance(instruction, str)
        
        # アサーション: プロンプトに期待されるキーワードが含まれていること
        self.assertIn("ASMR scriptwriter", instruction)
        self.assertIn("based on the situation given", instruction)
        
        # アサーション: ユーザー入力が追記されることを想定した基本構造になっていること
        self.assertTrue(instruction.endswith("gentle, 2nd person, PG-13.\n\n"))

if __name__ == '__main__':
    unittest.main()
