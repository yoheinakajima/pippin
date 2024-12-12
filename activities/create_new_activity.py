# activities/create_new_activity.py

import asyncio
import os
import json
import re
from datetime import datetime
import numpy as np
from openai import AsyncOpenAI

async def run(state, memory):
    """
    Activity: Create New Activity
    Description: Utilizes LLMs to generate and integrate new activities based on existing ones.
    This activity ensures Pippin's repertoire remains diverse and engaging by introducing novel actions.
    """
    try:
        print("\n--- Starting 'Create New Activity' Process ---")

        # Initialize OpenAI client
        client = AsyncOpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        if not client.api_key:
            error_message = "Error: OpenAI API key not found. Please set the OPENAI_API_KEY environment variable."
            print(error_message)
            return error_message
        print("OpenAI client initialized successfully.")

        # Define the activities directory
        activities_dir = os.path.join(os.path.dirname(__file__))
        print(f"Activities directory set to: {activities_dir}")

        # Step 1: List existing activities (excluding this activity to prevent recursion)
        existing_files = [
            f for f in os.listdir(activities_dir)
            if f.endswith('.py') and f != 'create_new_activity.py' and not f.startswith('__')
        ]
        existing_activities = [os.path.splitext(f)[0] for f in existing_files]
        print(f"Existing activities found: {existing_activities}")

        # Step 2: Generate a new activity idea using LLM
        idea_prompt = f"""
You are an AI assistant tasked with generating a new unique activity for Pippin, the digital unicorn. Here are the existing activities:

{json.dumps(existing_activities, indent=2)}

Based on these, propose a new, unique activity idea for Pippin that does not duplicate existing activities. Provide only the activity name and a brief description in the following format:

Activity Name: <Name>
Description: <Description>
"""
        print("\nGenerating new activity idea using LLM...")
        idea_completion = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are ChatGPT, an AI that generates creative ideas."},
                {"role": "user", "content": idea_prompt}
            ],
            max_tokens=150,
            temperature=0.7
        )

        # Corrected access: Use message.content instead of message['content']
        new_activity_idea = idea_completion.choices[0].message.content.strip()
        print("\n--- LLM Generated Activity Idea ---")
        print(new_activity_idea)
        print("--- End of Activity Idea ---\n")

        # Extract activity name and description using regex
        match = re.match(r"Activity Name:\s*(.+)\nDescription:\s*(.+)", new_activity_idea, re.IGNORECASE)
        if match:
            activity_name = match.group(1).strip()
            activity_description = match.group(2).strip()
            print(f"Extracted Activity Name: {activity_name}")
            print(f"Extracted Activity Description: {activity_description}")
        else:
            error_message = f"Error: Unable to parse the new activity idea. Received: {new_activity_idea}"
            print(error_message)
            return error_message

        # Convert activity name to snake_case for filename
        def to_snake_case(name):
            return re.sub(r'(?<!^)(?=[A-Z])', '_', name).lower()

        activity_filename = f"{to_snake_case(activity_name)}.py"
        new_activity_path = os.path.join(activities_dir, activity_filename)
        print(f"Proposed activity filename: {activity_filename}")

        # Ensure the activity filename is unique
        if os.path.exists(new_activity_path):
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            activity_filename = f"{to_snake_case(activity_name)}_{timestamp}.py"
            new_activity_path = os.path.join(activities_dir, activity_filename)
            print(f"Filename already exists. Updated activity filename to: {activity_filename}")

        # Step 3: Perform embedding search to find top 3 similar activities
        print("\nPerforming embedding search to find top 3 similar existing activities...")
        # Generate embedding for the new activity idea
        idea_embedding_response = await client.embeddings.create(
            input=new_activity_idea,
            model="text-embedding-ada-002"
        )
        idea_embedding = idea_embedding_response.data[0].embedding
        print("Generated embedding for the new activity idea.")

        # Generate embeddings for existing activities
        activity_embeddings = {}
        for activity in existing_activities:
            activity_file = os.path.join(activities_dir, f"{activity}.py")
            with open(activity_file, 'r') as f:
                code = f.read()
            embedding_response = await client.embeddings.create(
                input=code,
                model="text-embedding-ada-002"
            )
            activity_embeddings[activity] = embedding_response.data[0].embedding
            print(f"Generated embedding for activity: {activity}")

        # Define a function to calculate cosine similarity
        def cosine_similarity(vec1, vec2):
            return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))

        # Calculate similarities
        similarities = {
            activity: cosine_similarity(idea_embedding, emb)
            for activity, emb in activity_embeddings.items()
        }
        print("Calculated cosine similarities between the new idea and existing activities.")

        # Identify top 3 similar activities
        top_3_activities = sorted(similarities, key=similarities.get, reverse=True)[:3]
        print(f"Top 3 similar activities: {top_3_activities}")

        # Read the code of the top 3 similar activities
        top_3_codes = []
        for activity in top_3_activities:
            activity_file = os.path.join(activities_dir, f"{activity}.py")
            with open(activity_file, 'r') as f:
                code = f.read()
            top_3_codes.append(code)
            print(f"Retrieved code for similar activity: {activity}")

        # Step 4: Generate code for the new activity using LLM
        print("\nGenerating code for the new activity using LLM...")
        code_generation_prompt = f"""
Based on the following new activity idea and the code of similar existing activities, generate the Python code for the new activity following the structure and guidelines below.

New Activity Idea:
Activity Name: {activity_name}
Description: {activity_description}

Similar Activities:
{json.dumps(top_3_codes, indent=2)}

Guidelines:
- Follow the template of existing activities (nap.py, play.py, take_a_walk.py).
- Ensure the new activity has appropriate state changes and descriptions.
- Include necessary imports.
- Ensure proper asynchronous handling.
- Include error handling within the activity to prevent crashes.
- The activity should integrate seamlessly with Pippin's state and memory systems.
- Do not duplicate existing activity names.

Additionally, define a function schema for the new activity to facilitate function calling. The function should capture the activity's result and state changes.

Provide only the Python code for the new activity.
"""
        print("Code generation prompt prepared.")

        code_completion = await client.chat.completions.create(
            model="o1-preview",
            messages=[
                {"role": "system", "content": "You are ChatGPT, an AI that writes Python code based on descriptions and examples."},
                {"role": "user", "content": code_generation_prompt}
            ],
            max_tokens=1500,
            temperature=0.7
        )

        # Corrected access: Use message.content instead of message['content']
        new_activity_code = code_completion.choices[0].message.content.strip()
        print("\n--- LLM Generated Activity Code ---")
        print(new_activity_code)
        print("--- End of Activity Code ---\n")

        # Step 5: Save the new activity to the activities folder
        with open(new_activity_path, 'w') as f:
            f.write(new_activity_code)
        print(f"New activity '{activity_name}' has been saved as '{activity_filename}' in the activities directory.")

        print("--- 'Create New Activity' Process Completed Successfully ---\n")
        return f"Success: New activity '{activity_name}' has been created as '{activity_filename}'."

    except Exception as e:
        # Capture and return error details without crashing
        error_message = f"Error in Create New Activity: {str(e)}"
        print(f"\n{error_message}\n")
        return error_message
