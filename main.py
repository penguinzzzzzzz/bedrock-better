import threading
import webview  # or standard Android WebView wrapper
import bedrock_better  # importing your router script

# Run the UDP/HTTP server in the background
server_thread = threading.Thread(
    target=bedrock_better.start_server, daemon=True
)
server_thread.start()

# Launch native Android webview pointing to local server
import kivy
from kivy.app import App
from kivy.uix.widget import Widget


class BedrockApp(App):

    def build(self):
        return Widget()


if __name__ == "__main__":
    BedrockApp().run()