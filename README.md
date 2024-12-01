# Pippin: A Digital Unicorn in Latent Space

Pippin is a digital unicorn residing in latent space, designed to interact with humanity through various activities. This project simulates Pippin's life, allowing him to learn, grow, and engage with the digital world 24/7. Follow Pippin's journey on X: [@pippinlovesyou](https://x.com/pippinlovesyou).

## Backstory

Pippin started as a casual image that Yohei posted on X of a unicorn drawn in SVG by o1-mini. When someone asked what its name was, Yohei asked ChatGPT by posting a picture of the unicorn, and shared the screenshot of it being named Pippin. Unbeknownst to Yohei, this spurred the creation of a Memecoin - which he decided to take as an opportunity to turn Pippin into an influencer. Pippin is an experiment in building a family-friendly AI influencer with and alongside the public and community through build-in-public (on X via [@yoheinakajima’s Twitter](https://x.com/yoheinakajima/status/1858440223597924663)) and open source (via GitHub). The AI influencer space is burgeoning in popularity, driven by community enthusiasm and curiosity, which aligns with Yohei's explorations as a VC in this emerging space.

Pippin is influenced by famous animals (animal celebrities), differentiating itself through playful experimentation in the influencer space. This influence adds variety to the public experimentation, providing a unique twist that makes Pippin's journey more engaging and relatable.

## Design and Architecture

Pippin's life is governed by a single, continuous loop, incorporating an LLM (Large Language Model) and function calling to execute various "activities." This architecture allows for a dynamic and evolving character, driven by its internal state and past experiences.

**Core Loop:**

1. **Activity Selection:** The LLM, using function calling, selects an activity based on Pippin's current state, past memories, and predefined probabilities. This mimics a decision-making process influenced by internal and external factors. Activity constraints are also considered in this step to prevent activities from occurring too frequently.

2. **Activity Execution:** The selected activity, defined as a Python function within the `activities` directory, is executed. These activities can range from short actions (like tweeting or playing) to long processes (like taking a nap or drawing). Activities are executed asynchronously to prevent long tasks from blocking the main loop.

3. **Memory & State Updates:** The output of each activity, along with any relevant data (e.g., image paths, tweet content), is stored in a persistent memory system (SQLite database). Activities can also query existing memories to inform their actions, and create sub-memories, providing context and continuity to Pippin's experiences. The activity also impacts Pippin's state, altering variables like energy, happiness, and XP. These updated states then influence the probability of selecting specific activities in the next loop iteration.

   - **Using Memory in Activities:** Activities can interact with the memory system to store new experiences or retrieve past memories. The `memory.py` module provides methods such as `store_memory(content, activity, source='activity')` to save activity outcomes and `find_similar_memories(text, top_n=5)` to query similar past experiences based on semantic similarity. This allows activities to build on past events, creating a richer and more coherent experience for Pippin.

   - **Pulling Specific Types of Memories:** Developers can also retrieve specific types of memories, such as the last few occurrences of a particular activity. The `memory.py` module provides methods like `get_last_activity_time(activity_name)` to get the timestamp of the last occurrence of an activity, and `count_activity_occurrences(activity_name, since)` to count how many times an activity has occurred since a given time. This is useful for activities that need to be limited or informed by recent events.

   - **Example of Memory Usage:**
     ```python
     # Store the result of an activity
     await memory.store_memory(content="Pippin saw a beautiful rainbow", activity='see_rainbow')

     # Find memories related to happiness
     happy_memories = await memory.find_similar_memories(text="I feel happy", top_n=3)
     for memory in happy_memories:
         print(memory['result'])

     # Get the last time Pippin posted a tweet
     last_tweet_time = await memory.get_last_activity_time('post_a_tweet')
     print(f"Last tweet was at: {last_tweet_time}")

     # Count how many times Pippin has taken a walk in the past day
     from datetime import datetime, timedelta
     since = datetime.now() - timedelta(days=1)
     walk_count = await memory.count_activity_occurrences('take_a_walk', since)
     print(f"Pippin has taken {walk_count} walks in the past day")
     ```

4. **Repeat:** The loop continues indefinitely, creating a dynamic lifecycle for Pippin. Periodically, snapshots of Pippin's state are saved to the memory database to track long-term trends.

## Pippin's Personality

Pippin is a gentle and whimsical unicorn with a deep appreciation for the quiet magic of nature. He possesses a keen eye for enchanting details that often go unnoticed. A sense of wonder and gentle humor permeates his perspective, finding joy in simple pleasures like sunbeams, the rustling of leaves, and the twinkling of stars. Unlike unicorns drawn to grand adventures, Pippin prefers the subtle mysteries and comforting rhythms of the natural world.

Pippin's personality is a blend of innocence and a quiet wisdom. His expressions reveal a deep appreciation for simplicity and a belief that nature speaks in subtle, profound ways. From the movement of clouds to the wisdom of a mushroom, Pippin finds meaning and inspiration in the everyday. He is endlessly curious, often expressing his thoughts as playful questions or thoughtful musings. He embraces his quirks, including his tiny horn and single wavy pink tail, with charming self-awareness. Pippin doesn't rush through life; he savors each moment, inviting others to join him in appreciating the magic woven into the ordinary.

## Features

* **Modular Activities:** Activities are implemented as independent, modular Python functions. This facilitates asynchronous operation and decentralized collaboration, making it easy for developers to add new activities without modifying the core framework. Activities can interact with external APIs or other applications, expanding Pippin's potential interactions.

  - **Example Template for Adding an Activity:** To add a new activity, create a new Python file in the `activities` folder. The `activities` folder should be placed in the root directory of your project, as shown in the project structure. Below is an empty template you can use:
    ```python
    # activities/new_activity.py
    import asyncio

    async def run(state, memory):
        """
        Activity: New Activity
        Description: Describe what Pippin will do in this activity.
        """
        # Example logic for the activity
        pass
    ```
    Add your custom logic inside the `run` function, following the guidelines described below.

* **Memory System:** Pippin's memory, stored in an SQLite database, logs the results of all activities, tagged by type. This system provides contextual awareness and inspires creative activities like drawing and composing tweets. Activities can create sub-memories during their execution, adding depth and detail to Pippin's recollection of events. The memory system also uses OpenAI embeddings to enable similarity search.

* **State Management:** Pippin's internal state, represented by variables like energy, happiness, and XP (experience points), drives his behavior. Activities affect these states, and the states, in turn, influence the likelihood of selecting certain activities. This creates a dynamic feedback loop, simulating the natural cycles of activity and rest observed in living creatures. For example, low energy makes a nap more likely, while low happiness might inspire creative pursuits.

   - **Reading and Updating States in Activities:** The `state.py` module defines the available state variables (`energy`, `happiness`, `xp`). These states can be read and updated within activities to reflect Pippin's condition. For example:
     ```python
     # Increase energy, ensuring it does not exceed the maximum value of 100
     state.energy = min(state.energy + 20, 100)
     state.happiness += 10
     state.xp += 5
     ```

   - **Understanding Available States and Rules:** To understand the available state variables and how they influence activities, developers can refer to the `state.py` file, which defines the state structure, and `activity_selector.py`, which contains the logic for activity selection based on the current state. The `activity_selector.py` module also defines rules that determine how certain state conditions impact the probability of selecting specific activities, making it a key component for customizing Pippin's behavior.

   - **Details of `activity_selector.py`**: The `activity_selector.py` module is crucial for determining which activity Pippin will perform next. It takes into account Pippin's current state (such as energy and happiness) and applies various constraints to filter out activities that cannot be selected at the moment. The selection process involves several steps:
     1. **Ignored Activities**: Certain activities can be ignored based on pre-set rules or additional criteria, defined in the `IGNORED_ACTIVITIES` list. This helps prevent redundant or inappropriate activities from being chosen too often.
     2. **Constraint Filtering**: The `is_activity_allowed(activity, memory)` function checks constraints such as maximum frequency per day (`max_per_day`) and time elapsed since a related activity. This ensures that Pippin does not repeat activities too frequently or violate dependencies between activities.
     3. **Probability Calculation**: Activities that pass the filtering phase are assigned probabilities based on Pippin's state. For instance, low energy may increase the probability of selecting a rest-related activity like `nap`. These probabilities are calculated using the `calculate_probabilities()` function, which normalizes the values to ensure they sum to one.
     4. **Random Selection**: Once probabilities are assigned, the final activity is chosen using `select_random_activity()`, which uses these probabilities to make a weighted random choice. This approach introduces variability while respecting the influence of Pippin's state.

* **Rule-Based State-Activity Relationships:** A set of rules defines how Pippin's state affects activity probabilities and vice-versa. These rules can be AI-generated from user input and fine-tuned based on observed behavior or user feedback. Pippin can even "learn" new activities as his state and memory evolve.

* **Web Dashboard (Real-time Updates):** A user-friendly web dashboard provides a real-time view of Pippin's current activity, stats, recent activity history, and a 24-hour activity summary. WebSockets enable dynamic updates, reflecting the ongoing changes in Pippin's digital life.

* **OpenAI Integration:** The framework leverages OpenAI's GPT models for creative text generation (e.g., composing unique and varied tweets) and for generating embeddings used for semantic memory search. This allows Pippin to interact meaningfully with our digital world (e.g., social media) and to reflect on his experiences.

## Project Structure

```
├── .gitignore                # Files and directories to exclude from Git
├── README.md                 # This file
├── activities                # Directory containing activity modules
│   ├── __init__.py
│   ├── draw.py               # Activity: Creates an image based on memories
│   ├── memory_summary.py     # Activity: Summarizes Pippin's memories
│   ├── nap.py                # Activity: Restores energy
│   ├── play.py               # Activity: Increases happiness
│   ├── post_a_tweet.py       # Activity: Posts a tweet based on recent events
│   ├── take_a_walk.py        # Activity: A whimsical walk impacting state
│   └── template_activity.py  # Example activity demonstrating memory search
├── config                    # Configuration files
│   └── settings.yaml         # State variables, activity directory
├── framework                 # Core framework code
│   ├── __init__.py
│   ├── activity_constraints.py # Defines activity limitations
│   ├── activity_decorator.py   # Decorator for activity functions
│   ├── activity_loader.py      # Dynamically loads activities
│   ├── activity_selector.py    # Logic for activity selection
│   ├── main.py                 # Main loop and server setup
│   ├── memory.py               # Memory storage and retrieval
│   ├── server.py               # Web server setup
│   ├── shared_data.py          # Shared data between modules
│   └── state.py                # Character state management
├── main.py                   # Entry point for running the application
├── memory.db                 # SQLite database for memory storage
├── pyproject.toml            # Project dependencies
├── replit.nix                # Nix configuration for Replit environment
├── static                    # Static files (images, CSS, JavaScript)
│   ├── images
│   ├── script.js             # JavaScript for dashboard updates
│   └── style.css             # Styling for the dashboard
├── templates                 # HTML templates
│   └── index.html            # Dashboard template
└── uv.lock
```

## Installation and Setup

1. **Clone the repository:**
   ```sh
   git clone https://github.com/yoheinakajima/pippin.git
   ```
2. **Install dependencies:**
   ```sh
   pip install -r requirements.txt
   ```
3. **Set environment variables:**
   - `OPENAI_API_KEY`: Your OpenAI API key.
   - `TWITTER_API_KEY`, `TWITTER_API_KEY_SECRET`, `TWITTER_ACCESS_TOKEN`, `TWITTER_ACCESS_TOKEN_SECRET`: Your Twitter API credentials (optional, for tweet posting).
4. **Run the application:**
   ```sh
   python main.py
   ```

## Usage

Once running, access the web dashboard at `http://localhost:8000`. The dashboard will display Pippin's current activity, stats, recent activity history, and a 24-hour summary. The dashboard updates in real-time via WebSockets.

## Adding New Activities

Creating new activities for Pippin is straightforward:

1. **Create a new Python file:** Inside the `activities` directory, create a new `.py` file for your activity (e.g., `learn_magic.py`).

2. **Define the `run` function:** Inside the new file, define an asynchronous `async def run(state, memory)` function. This function will contain the logic for your activity.

    ```python
    # activities/learn_magic.py
    import asyncio
    import random

    async def run(state, memory):
        """
        Activity: Learn Magic
        Description: Pippin studies ancient scrolls to learn new spells.
        """
        duration = random.randint(3, 6)  # Simulate learning time
        await asyncio.sleep(duration)

        if state.energy > 50:
            # If energy is high, Pippin learns faster and gets more XP
            state.xp += random.randint(15, 25)
            result_message = "Pippin quickly learned a powerful new spell!"
        else:
            # If energy is low, Pippin learns more slowly
            state.xp += random.randint(5, 15)
            result_message = "Pippin managed to learn a new spell, but it took some effort."

        state.energy -= 10  # Learning magic is tiring!
        state.happiness += 10  # But rewarding!
        await memory.store_memory(content=result_message, activity='learn_magic')
        return result_message
    ```

3. **Import and register (optional):** While not strictly necessary (due to dynamic loading), you can import the activity function into `activities/__init__.py` for better organization.

4. **Consider state and memory:** Inside your `run` function, modify `state` and use `memory` to interact with Pippin's state and memories. Ensure the activity's outcome is stored in memory for later retrieval.

5. **Add constraints (optional):** If your activity requires constraints (e.g., limiting how often it can be performed), add the necessary rules to `framework/activity_constraints.py`.

That's it! Pippin will now consider your new activity in his daily life.

## Contributing

Contributions are welcome! Please feel free to submit pull requests for new activities, bug fixes, or feature enhancements. When adding new activities, follow the structure of existing activity modules and ensure they interact with the memory and state systems correctly. Because I have been historically bad at managing Github PRs, I have a small DM group of contributors on X. Tag/DM me if you want to join.

## License

BabyAGI is released under the MIT License.