import argparse
from groq import Groq

parser = argparse.ArgumentParser()
parser.add_argument("--prompt", required=True)
parser.add_argument("--api-key", required=True)
args = parser.parse_args()

client = Groq(api_key=args.api_key)

response = client.chat.completions.create(
    model="openai/gpt-oss-120b",
    messages=[{"role": "user", "content": args.prompt}],
    temperature=0,
    max_tokens=500,
)

print(response.choices[0].message.content)
