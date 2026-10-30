"""
Crowd Safety Monitor - Presentation Generator Dispatcher
Builds the 14-slide widescreen (16:9) final review presentation deck.
"""
from generate_final_presentation import build_presentation

if __name__ == "__main__":
    target_files = [
        "Crowd_Safety_Monitor_Final_Review.pptx",
        "Crowd_Safety_Monitor_Review2_Extended.pptx",
        "Crowd_Safety_Monitor_Review2.pptx"
    ]
    build_presentation(target_files)
