# ========================================================================
# Gen-AI Workshop: Automatic Detection of Misplaced Business Logic in Java
# ========================================================================
# This single notebook covers RAG, Agents, and Workflows for analyzing Java code against Clean Architecture rules.
# Focus: Detect/explain violations (e.g., business logic in controllers/repos) in legacy projects.
# Run cells sequentially; add your OpenAI key below. Hands-on: Tweak code snippets to experiment.
# Tech: Python, OpenAI, sentence-transformers, FAISS, LangChain (minimal).

# Shared Setup: Installs and Data
# (Run this first; ~2 min)
#pip install sentence-transformers faiss-cpu openai langchain langchain-openai langchain-community

import re
import numpy as np
from sentence_transformers import SentenceTransformer
import faiss
from openai import OpenAI
from langchain_openai import ChatOpenAI
from langchain.agents import Tool, initialize_agent, AgentType
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain, SequentialChain
from langchain_core.runnables import RunnableLambda

# Read OpenAI API key from file (secure; not hardcoded)
try:
    with open('api-key.txt', 'r') as f:
        OPENAI_API_KEY = f.read().strip()
    print("API key loaded from file.")
except FileNotFoundError:
    raise FileNotFoundError("Upload 'api-key.txt' (containing just your OpenAI key) to Colab's file browser and re-run.")

# Mini Knowledge Base (architecture rules; same across sections)
KB_MARKDOWN = """
# Clean Architecture Rules for Java Applications

## Layering Principles
- **Domain Layer**: Contains business entities, rules, and logic. This is the core of the application, independent of frameworks or external systems.
- **Service Layer**: Implements business use cases by orchestrating domain objects. Business logic (e.g., calculations, validations, decisions) must reside here.
- **Controller/API Layer**: Handles incoming requests (e.g., HTTP), parses input, calls services, and returns responses. No business logic allowed—only orchestration and validation.
- **Repository Layer**: Manages data persistence (e.g., database queries). Should only handle CRUD operations, no business decisions or transformations.
- **UI Layer**: Presentation only (e.g., views, frontend). No business logic; delegate to services.

## Anti-Patterns for Misplaced Business Logic
- **Logic in Controllers**: If-statements, calculations, or decisions based on business rules in controllers (e.g., checking user age and applying discounts). Move to services.
- **Logic in Repositories**: Business transformations or validations in repo methods (e.g., filtering results based on business conditions). Keep repos data-only.
- **God Classes**: Single classes mixing layers (e.g., a controller querying DB and applying logic). Enforce separation.
- **Leaky Abstractions**: Adapters (e.g., controllers) leaking domain logic, leading to tight coupling and hard testing.

## Examples of Violations
- Violation: Controller contains if (user.balance < 0) { throw OverdraftException; } — This is business validation; move to AccountService.
- Correct: Controller calls service.checkBalance(userId), which handles the logic.

These rules improve maintainability, testability, and scalability in legacy Java projects.
"""

# Clean KB too, just in case
KB_MARKDOWN = KB_MARKDOWN.replace('\u200b', '').replace('\ufeff', '')

# RAG Components (shared across sections)
model = SentenceTransformer('all-MiniLM-L6-v2')
chunks = re.split(r'\n\s*\n', KB_MARKDOWN.strip())  # Split by paragraphs
embeddings = model.encode(chunks)
dimension = embeddings.shape[1]
index = faiss.IndexFlatL2(dimension)
index.add(np.array(embeddings))

def retrieve_relevant_rules(query):
    """Core retrieval function: Embed query, fetch top-3 chunks."""
    query_embedding = model.encode([query])
    _, indices = index.search(np.array(query_embedding), 3)
    relevant = "\n\n".join([chunks[i] for i in indices[0]])
    return relevant.replace('\u200b', '').replace('\ufeff', '')  # Clean output

# Sample Java Code Snippets (use these for hands-on; one clean, two leaky)
SAMPLES = {
    "clean": """
package com.example.controller;

import com.example.service.UserService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class UserController {

    private final UserService userService;

    public UserController(UserService userService) {
        this.userService = userService;
    }

    @GetMapping("/users/{id}")
    public User getUser(@PathVariable Long id) {
        return userService.getValidatedUser(id);
    }
}
""",
    "leaky_controller": """
package com.example.controller;

import com.example.repository.UserRepository;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class UserController {

    private final UserRepository userRepository;

    public UserController(UserRepository userRepository) {
        this.userRepository = userRepository;
    }

    @GetMapping("/users/{id}")
    public User getUser(@PathVariable Long id) {
        User user = userRepository.findById(id);
        if (user.getAge() < 18) {
            throw new RuntimeException("User is minor; access denied.");  // Misplaced business logic
        }
        user.setDiscount(user.getAge() > 65 ? 0.2 : 0.0);  // Misplaced calculation
        return user;
    }
}
""",
    "leaky_repository": """
package com.example.repository;

import com.example.entity.User;
import org.springframework.data.jpa.repository.JpaRepository;

public interface UserRepository extends JpaRepository<User, Long> {

    default User findValidatedById(Long id) {
        User user = findById(id).orElseThrow();
        if (user.getBalance() < 0) {
            user.setStatus("overdue");  // Misplaced business logic
        }
        return user;
    }
}
"""
}

# Clean samples too
for key in SAMPLES:
    SAMPLES[key] = SAMPLES[key].replace('\u200b', '').replace('\ufeff', '')

print("Setup complete. Proceed to sections below.")

# ========================================================================
# Section 1: RAG (Retrieval-Augmented Generation)
# ========================================================================
# Goal: Build a simple RAG pipeline to retrieve relevant rules based on Java code.
# Why? Augments LLM with domain knowledge (e.g., anti-patterns) to detect violations accurately.
# Hands-on: Run, then swap SAMPLES["clean"] for "leaky_controller" and re-run to see differences.

# Step 1: Retrieve rules for a sample
java_code = SAMPLES["leaky_controller"]  # Change this to experiment
relevant_rules = retrieve_relevant_rules(java_code)
print("Retrieved Rules:\n", relevant_rules[:500], "...")  # Truncated for brevity

# Step 2: Augment with LLM for analysis
client = OpenAI(api_key=OPENAI_API_KEY)
# Do not change the model! gpt-4.1-nano is a real model!
response = client.chat.completions.create(
    model="gpt-4.1-nano",
    messages=[
        {"role": "system", "content": "You are a Java architecture expert using RAG-retrieved rules."},
        {"role": "user", "content": f"Code:\n{java_code}\n\nRules:\n{relevant_rules}\n\nList violations with locations and explanations."}
    ]
)
print("\nRAG-Enhanced Analysis:\n", response.choices[0].message.content)

# Exercise: Modify java_code to SAMPLES["clean"]—what changes? How might you improve chunking for better retrieval?

# ========================================================================
# Section 2: Agents
# ========================================================================
# Goal: Create a simple agent that reasons step-by-step, using the RAG tool to gather context before analyzing.
# Why? Agents add autonomy—e.g., decide if/when to retrieve rules based on code complexity.
# Builds on RAG: Wraps retrieve_relevant_rules as a tool.
# Hands-on: Run, then try SAMPLES["leaky_repository"] and observe agent's verbose thinking.

# Define agent tools (RAG as the key tool)
tools = [
    Tool(
        name="RetrieveArchitectureRules",
        func=retrieve_relevant_rules,
        description="Retrieve Clean Architecture rules and anti-patterns for a given Java code snippet."
    )
]

# Initialize agent
llm = ChatOpenAI(model="gpt-4o-mini", api_key=OPENAI_API_KEY)
agent = initialize_agent(
    tools, llm, agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION, verbose=True  # Shows reasoning
)

# Run agent on sample
java_code = SAMPLES["leaky_repository"]  # Experiment here
prompt = f"Analyze this Java code for misplaced business logic violations: {java_code}"
result = agent.run(prompt)
print("\nAgent's Final Analysis:\n", result)

# Exercise: Add a second tool (e.g., a mock "suggest_fix" function) and see how the agent adapts. Does it always call the tool?

# ========================================================================
# Section 3: Workflows
# ========================================================================
# Goal: Orchestrate a fixed sequence (workflow) of steps: Retrieve -> Analyze -> Output.
# Why? Workflows ensure reliable pipelines for production-like automation (e.g., CI/CD code checks).
# Builds on prior: Chains RAG + LLM analysis using SequentialChain.
# Hands-on: Run, then input custom code and trace the verbose flow.

# LLM setup
llm = ChatOpenAI(model="gpt-4o-mini", api_key=OPENAI_API_KEY)

# Chain 1: Retrieval (wrapped as runnable)
retrieval_runnable = RunnableLambda(lambda inputs: {"rules": retrieve_relevant_rules(inputs["code"])})

# Chain 2: Analysis
analysis_prompt = PromptTemplate.from_template(
    "Code: {code}\nRules: {rules}\n\nExplain violations: locations, citations, and why it matters for maintainability."
)
analysis_chain = LLMChain(llm=llm, prompt=analysis_prompt, output_key="analysis")

# Full workflow: Sequential chain
workflow = SequentialChain(
    chains=[retrieval_runnable, analysis_chain],
    input_variables=["code"],
    output_variables=["analysis"],
    verbose=True  # Logs each step
)

# Run on sample
java_code = SAMPLES["clean"]  # Or your own leaky example
result = workflow({"code": java_code})
print("\nWorkflow Output:\n", result["analysis"])

# Exercise: Extend the chain (e.g., add a summarization step). Input a "god class" snippet—what violations emerge?

# ========================================================================
# Wrap-Up: Next Steps for Your Team
# ========================================================================
# - Integrate into CI/CD: Hook this to GitHub Actions for commit scans.
# - Scale: Use larger embeddings (e.g., for full repos) or fine-tune on your codebase.
# - Q&A: Discuss pain points—how does this address leaky logic in your projects?
# Thanks for participating—feedback welcome!