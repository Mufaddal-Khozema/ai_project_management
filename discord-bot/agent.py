import os
import json
from dotenv import load_dotenv
from google import genai
from google.genai import types
from taiga_client import TaigaClient

load_dotenv()

GEMINI_MODEL=os.getenv("GEMINI_MODEL")
client= genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

taiga= TaigaClient(os.getenv("TAIGA_URL"),os.getenv("TAIGA_USER"),os.getenv("TAIGA_PASS"))

TOOLS= types.Tool(function_declarations = [

    # tool for create an item in the project
    types.FunctionDeclaration(
        name= "create_item",
        description= "Create a new issue, task, user story or epic in Taiga.",
        parameters= {
            "type":"object",
            "properties": {
                "resource":{
                    "type":"string",
                    "enum": ["issues","tasks","userstories","epics"],
                },
                "subject": {"type": "string"},
                "description": {"type": "string"},
            },
            "required":["resource", "subject"],
        },
    ),
])

def execute_tool(name,args,project_id):
    if name == "create item":
        payload={"project":project_id, "subject": args["subject"],"description":args.get("description","")}
        return taiga.create(args["resource"],payload)
    raise ValueError(f"Unknown tool: {name}")


def run_agent(user_message, project_id):
    contents=[types.Content(role="user", parts=[types.Part.from_text(text=user_message)])]

    config= types.GenerateContentConfig(
        tools=[TOOLS],
        automatic_function_calling= types.AutomaticFunctionCallingConfig(disable=True),
        system_instruction=(
            "You are a Taiga project assisstant. Use the available tools to fulfil the user's request."
        ),
    )

    for _ in range(5):
        response=client.models.generate_content(
            model=GEMINI_MODEL, contents=contents, config=config,
        )

        if not response.function_calls:
            return response.text
        
        contents.append(response.candidates[0].content)

        function_response_parts =[]
        for fc in response.function_calls:
            name,args = fc.name, fc.args

        try:
            result = execute_tool(name, args, project_id)
        except Exception as e:
            result = {"error": str(e)}

        function_response_parts.append(
            types.Part.from_function_response(name=name, response={"result": result})
        )

        contents.append(types.Content(role = "tool", parts= function_response_parts))
    
    return "Sorry, I couldn't complete that after several attempts."


