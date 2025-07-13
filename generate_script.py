# To run this code you need to install the following dependencies:
# pip install google-genai

import base64
import os
from google import genai
from google.genai import types


def generate():
    client = genai.Client(
        api_key=os.environ.get("GEMINI_API_KEY"),
    )

    model = "gemini-2.5-flash"
    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text="""# 指示
あなたはプロの脚本家です。この後に入力される物語の設定を参考に、脚本を生成してください。

# 注意事項
状況の解説をする situation explainer が 1 人、物語内で実際に話す main character が 1 人存在する。
それぞれは、会話の中で干渉しない。

# 出力形式
脚本は以下の JSON format でのみ出力すること。
{
  \"situation\": \"sample situation\",
  \"scene_elements\": [
    {
      \"speaker\": \"situation explainer\",
      \"script\": \"sample situation explanation\"
    },
    {
      \"speaker\": \"main character\",
      \"script\": \"sample script\"
    },
    {
      \"speaker\": \"situation explainer\",
      \"script\": \"sample situation explanation\"
    },
    {
      \"speaker\": \"main character\",
      \"script\": \"sample script\"
    }
  ]
}

# 物語の設定
寝る前に恋人が、彼氏に愛情を伝えるシーン
"""),
                types.Part.from_text(text="""INSERT_INPUT_HERE"""),
            ],
        ),
    ]
    generate_content_config = types.GenerateContentConfig(
        thinking_config = types.ThinkingConfig(
            thinking_budget=-1,
        ),
        response_mime_type="application/json",
    )

    response = client.models.generate_content(model=model, contents=contents, config=generate_content_config)
    output_dir = "scripts"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    file_index = len(os.listdir(output_dir))
    output_file = os.path.join(output_dir, f"script_{file_index}.json")
    with open(output_file, "w") as f:
        f.write(response.text)
    print(f"スクリプトを {output_file} に保存しました。")


if __name__ == "__main__":
    generate()
