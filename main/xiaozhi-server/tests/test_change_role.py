import unittest
from types import SimpleNamespace

from plugins_func.functions.change_role import change_role


class ChangeRoleTests(unittest.TestCase):
    def make_conn(self):
        conn = SimpleNamespace(prompt=None)

        def change_system_prompt(prompt):
            conn.prompt = prompt

        conn.change_system_prompt = change_system_prompt
        return conn

    def test_uses_role_name_as_selected_role(self):
        conn = self.make_conn()

        result = change_role(conn, role_name="好奇小男孩", role="学生")

        self.assertEqual(result.response, "切换角色成功，我是好奇小男孩")
        self.assertIn("8岁小男孩", conn.prompt)

    def test_supports_legacy_role_parameter(self):
        conn = self.make_conn()

        result = change_role(conn, role_name="Lily", role="英语老师")

        self.assertEqual(result.response, "切换角色成功，我是Lily")
        self.assertIn("Lily", conn.prompt)


if __name__ == "__main__":
    unittest.main()
