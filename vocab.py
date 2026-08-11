import argparse
from groq import Groq

def generate(prompt, api_key):
    client = Groq(api_key=api_key)
    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=1500,
    )
    return response.choices[0].message.content

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--api-key", required=True)
    args = parser.parse_args()
    print(generate(args.prompt, args.api_key))

if __name__ == "__main__":
    main()
