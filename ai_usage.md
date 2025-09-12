# AI Usage Document - Fintech Payouts Application

## Project Overview

This document details the AI-assisted development process for building a secure, observable, and reliable full-stack fintech application. The project implements OAuth 2.0 authentication, payout processing with mock third-party providers, webhook handling, and comprehensive observability features.

## AI Tools and Agents Used

### Primary AI Assistant: Cursor
- **Usage**: Main tool for actual code writing, implementation, and debugging
- **Context**: Used throughout the development process for code generation, refactoring, and problem-solving
- **Features**: Leveraged Cursor's AI-powered code completion, chat functionality, and code suggestions
- **Project Rules**: Created comprehensive development rules and guidelines via `.cursor/rules` to ensure consistent code quality and architectural patterns

### Planning and Architecture: ChatGPT
- **Usage**: Primary tool for project planning, architecture design, and high-level strategy
- **Context**: Used for initial project planning, architectural decisions, and technical approach validation



### Requirements Analysis and Framework Selection Process

**Initial Requirements Clarification**:
ChatGPT was instrumental in helping understand and break down the complex fintech requirements. The process involved:


2. **Architectural Framework Decision**:
   - **Backend Framework**: ChatGPT helped evaluate FastAPI vs Flask vs Django for fintech applications
 
   - **Database Selection**: Helped in deciding how I was going to create a postgres instance
  -  **Backend Library Selection**: ChatGPT was crucial in selecting the right libraries and dependencies for the backend implementation especially since my experience in building production quality python backends are limited:
   
   - **Database ORM**: Evaluated SQLAlchemy vs Tortoise ORM vs Databases library
     - SQLAlchemy selected for its mature async support, comprehensive features, and Alembic migration support
   
   - **Authentication Libraries**: Analyzed python-jose vs PyJWT vs Authlib for JWT handling
     - python-jose chosen for its comprehensive JWT support and OAuth 2.0 compatibility
   
   
   - **Database Driver**: Evaluated asyncpg vs psycopg2 vs psycopg3
     - asyncpg chosen for its pure async implementation and performance benefits

4. **Technology Stack Validation**:
   - Used ChatGPT to validate the chosen stack against fintech industry standards
   - Analyzed security implications of each technology choice
   - Considered scalability and maintainability factors

This planning phase with ChatGPT ensured a solid foundation before moving to implementation with Cursor.
#### Cursor Rules Configuration

**Development Guidelines Creation**:
Comprehensive development rules in `.cursor/rules` that guided the entire development process:

- **Coding Standards**: Established Python/FastAPI best practices, TypeScript/React conventions, and security guidelines
- **Architecture Patterns**: Defined consistent patterns for API design, error handling, and database operations
- **Security Requirements**: Specified OAuth 2.0 implementation standards, webhook verification, and input validation rules
- **Observability Standards**: Established logging patterns, correlation ID usage, and error tracking requirements
- **Testing Guidelines**: Defined testing strategies, fixture patterns, and coverage requirements

These rules served as a constant reference during development with Cursor, ensuring consistent implementation of the planned architecture and maintaining high code quality standards throughout the project.

## Project Development Approach

### Phase-Based Development Strategy

After sketching out the full application flow end-to-end on a whiteboard, I broke the project into smaller, manageable phases to ensure systematic development and maintainable code quality.

**Initial Planning Process**:
1. **Whiteboard Flow Design**: Created a comprehensive end-to-end flow diagram covering:
   - OAuth 2.0 authentication flow
   - Payout creation and processing pipeline
   - Webhook handling and status updates
   - Error handling and retry mechanisms
   - Database interactions and state management

2. **Repository Structure Creation**: Manually created the entire repository structure following FastAPI and React best practices:
   - Separated concerns with dedicated directories for `api/`, `core/`, `db/`, `models/`, `schemas/`, `services/`, `tests/`
   - Established clear separation between frontend and backend codebases
   - Set up proper configuration files and dependency management

3. **Phase-Based Implementation**: Fed Cursor my detailed plan to build the system in smaller, focused steps:

**Phase 1: Foundation**
- `core/config.py` - Environment settings with validation
- `core/logging.py` - Structured JSON logging with correlation IDs  
- `db/session.py` - Database connection and session management
- `main.py` - FastAPI app with middleware setup

**Implementation Strategy**:
- Made sure to clarify any questions Cursor had about requirements
- Requested multiple implementation options when necessary
- Built each component individually with focused attention
- Validated each phase before moving to the next

This approach ensured:
- **Incremental Progress**: Each phase built upon the previous foundation
- **Quality Control**: Individual component validation prevented cascading issues
- **Clear Dependencies**: Understanding of how each piece connected to the whole
- **Maintainable Architecture**: Proper separation of concerns from the start

## Project Breakdown and Workflow

After sketching the **end-to-end flow of the app** on a whiteboard, I divided the project into smaller, manageable phases.

### Repo Setup
- Created the repository structure by hand before starting.
- Fed Cursor my plan to build the system incrementally, phase by phase, below is a real prompt I used, remember cursor had the rules already setup for the overall project goals and standards.

This approach ensured the foundation was solid before moving to later phases.

### Example Prompt Backend
```This phase includes:

We are starting Phase 1: Foundation of the system.


core/config.py → Environment settings with validation

core/logging.py → Structured JSON logging with correlation IDs

db/session.py → Database connection and session management

main.py → FastAPI app with middleware setup

Here’s how I want you to approach this:

Clarify any assumptions or questions you have before generating code.

When there are multiple design choices (e.g., libraries, logging formats), provide me with clear options to choose from.

Build each of the above components individually, one file at a time, with complete implementations. As you go if you need me to clarfiy any questions ask
 ```

### Review of AI Outputs
To ensure correctness, security, and maintainability, all AI-generated outputs were carefully reviewed before integration into the codebase.  
The review process included:

1. **Validation Against Requirements**  
   - Verified that the generated code or documentation aligned with the assignment requirements and project goals.  

2. **Security Review**  
   - Checked AI outputs for secure handling of credentials, tokens, and sensitive data.  
   - Ensured OAuth 2.0 implementation followed recommended best practices (state, nonce, PKCE).  
   - Validated webhook verification logic against HMAC signing.  

3. **Code Quality Review**  
   - Ensured adherence to Python/JavaScript style guides and maintainable structure.  
   - Confirmed proper separation of concerns (e.g., FastAPI routes vs. database logic vs. schemas).  
   - Validated type-safety and data validation using Pydantic.  

4. **Testing & Verification**  
   - Manually tested endpoints, authentication flow, and webhook handling.  
   - Wrote additional unit tests for critical functions where AI-generated code was incomplete or ambiguous.  
   - Ensured migrations (Alembic) matched database schema expectations.  

5. **Refinement & Adjustments**  
   - In cases where AI outputs were partially correct, I refined code manually or prompted the AI for alternatives.  
   - Documented key design decisions where multiple AI-suggested options were considered.  

This review process ensured that AI contributions were accurate, secure, and production-ready before inclusion in the final project.

## AI Mistakes and Corrections

### Over-Engineering Database Models

**The Problem**: During the database design phase, Cursor generated overly complex database models and relationships that didn't align with the actual application flow requirements.

**What Happened**: 
- AI created intricate database schemas with unnecessary foreign key relationships
- Generated models with fields that weren't actually needed for the core payout flow
- Suggested complex indexing strategies that added complexity without clear benefit
- Created database abstractions that made the simple payout tracking more complicated than necessary

**The Correction Process**:
1. **Referred Back to Whiteboard**: I went back to my original whiteboard flow diagram to remind myself of the actual data flow requirements
2. **Manual Schema Design**: I sketched out the database models by hand, focusing only on what was actually needed:
   - Simple user table for OAuth integration
   - Straightforward payout table with essential fields (amount, currency, status, timestamps)
   - Basic webhook events table for tracking status updates
3. **Simplified Requirements**: Fed the simplified, hand-drawn schema back into Cursor with clear instructions:
   - "Build only these tables with these exact fields"
   - "No complex relationships - keep it simple"
   - "Focus on the actual payout flow, not theoretical edge cases"

**Key Learning**: The AI tended to over-engineer solutions when given broad requirements. By providing specific, simplified schemas based on actual flow analysis, I was able to get focused, appropriate implementations.

**Result**: The final database design was clean, maintainable, and perfectly aligned with the application's actual needs rather than theoretical complexity.

## Frontend AI Usage and Review
For the frontend, I set up the project by hand using **Vite** and created the folder structure manually.  
I then built each screen by prompting the AI with detailed descriptions of what I wanted rendered on the screen.  

During this process:  
- **Rejected Outputs**: The AI initially produced implementations using raw HTML and CSS. The generated CSS was overly complex, difficult to maintain, and not aligned with the component-based approach I wanted.  
- **Accepted Outputs**: After refining my prompts to specify Material UI (MUI), the AI generated React components styled with MUI. This was accepted as it simplified styling, improved consistency, and better aligned with modern frontend practices. At one stage, Tailwind was introduced without me requesting it; this was deemed unnecessary since MUI already provides robust component-level styling. For cases where finer control was needed, I supplemented MUI with small, targeted blocks of custom CSS.  

All accepted outputs were reviewed and refined to ensure clean structure, maintainability, and consistency with the project’s design standards.

### Example: Building the Payout Form with AI

One example of my workflow was creating the **Payout Form** component.  

**Initial Prompt to AI (Cursor):**  

```
Create a React payout form with fields for amount and currency selection, and a submit button. The form should validate input and prevent submission if the amount is invalid.
``` 

**AI Output (Rejected):**  
- The AI generated a plain HTML `<form>` with `<input>` and `<select>` elements styled using raw CSS.  
- The CSS was overly verbose, introduced global styles, and did not integrate with my component-driven approach.  

**Iteration & Refinement:**  
I updated my rules for prompts as I went along to filter out common mistakes made by the ai that didnt align with my goals.

**Accepted Output (Refined):**  
The AI then produced a React component using MUI’s `TextField`, `Button`, and `MenuItem`, aligned with my project’s styling approach. I integrated this into the `PayoutForm` and further refined:  
- Added accessibility attributes (e.g., `aria-label`, `aria-required`, `aria-live`).  
- Enforced constraints like `min`, `max`, and `step` for the amount field.  
- Centralized state management into a custom `usePayoutForm` hook for cleaner separation of concerns.  

This iterative process ensured the AI’s contributions were aligned with my coding standards and produced a clean, maintainable component. When reviewing AI-generated code, I often spotted small issues or opportunities to simplify logic. Instead of prompting again, I fixed these by hand.  

### Conclusion
Throughout this project, AI served as a valuable assistant for generating code, scaffolding components, and exploring design options. However, its outputs were never accepted blindly. Every contribution was validated against project requirements, security standards, and maintainability goals. By applying strict review, rejecting misaligned outputs, iterating on prompts, and making manual fixes where needed, I ensured the final system was clean, secure, and production-ready. The AI accelerated development, but the engineering responsibility and quality assurance always remained firmly with me.
