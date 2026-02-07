# Rolevo - AI-Powered Roleplay & Training Platform

Rolevo is a cutting-edge, AI-driven training platform designed to enhance professional skills through interactive roleplay scenarios. It leverages advanced AI models to simulate realistic conversations, allowing users to practice and improve their soft skills, sales techniques, and leadership abilities in a safe, controlled environment.

## 🚀 Key Features

### 🤖 AI Roleplay Engine
- **Realistic Simulations:** Engage in dynamic, voice-enabled or text-based conversations with AI characters powered by OpenAI's GPT-4o.
- **Voice Interaction:** Seamless speech-to-text (Whisper) and text-to-speech (AWS Polly / OpenAI Audio) integration for a natural conversational experience.
- **Adaptive Scenarios:** The AI adapts its responses based on user input and the specific scenario context.

### 📊 Competency-Based Assessment
- **Objective Scoring:** Users are evaluated on specific competencies defined for each roleplay scenario.
- **Detailed Feedback:** instant feedback on performance, highlighting strengths and areas for improvement.
- **Behavioral Analysis:** deeper insights into user behavior and communication style.

### 📑 Automated Performance Reports
- **Professional PDF Reports:** Automatically generates detailed performance reports after each session.
- **Email Delivery:** Reports are instantly emailed to users, containing score breakdowns, interaction transcripts, and personalized recommendations.
- **Visual Analytics:** Color-coded scores and easy-to-read charts help users track their progress.

### 🛠️ Admin & Management
- **Scenario Management:** Admins can easily create and modify roleplay scenarios, defining characters, contexts, and evaluation criteria.
- **User Management:** comprehensive dashboard to manage users, assign roleplays, and track organizational performance.
- **Cluster/Department Support:** Organize users into clusters or departments for targeted training programs.

## 💻 Technology Stack

- **Backend:** Python, Flask, SQLAlchemy
- **AI Core:** OpenAI GPT-4o, Whisper API
- **Voice Services:** AWS Polly, OpenAI TTS
- **Database:** MySQL
- **Reporting:** ReportLab (PDF Generation)
- **Frontend:** HTML5, CSS3, JavaScript (Vanilla)

## 🔧 Installation & Setup

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd Rolevo-flaskapp-firas
    ```

2.  **Create a virtual environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Environment Variables:**
    - Create a `.env` file based on `.env.example`.
    - Add your API keys (OpenAI, AWS) and database credentials.
    - Configure SMTP settings for email delivery.

5.  **Initialize the Database:**
    ```bash
    flask db upgrade
    ```

6.  **Run the Application:**
    ```bash
    flask run
    ```
    Access the app at `http://localhost:5000`.

## 🤝 Credits

- **OpenAI:** For the powerful GPT and Whisper models.
- **AWS:** For reliable text-to-speech services.
- **Flask:** For the robust web framework.

---
© 2025 Rolevo. All Rights Reserved.
