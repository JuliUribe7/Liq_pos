# theme.py
"""
Theme configuration for LiquorPOS
Colors inspired by modern dark UI design
"""

class Theme:
    # Background colors
    BG_DARK = "#050609"          # Main window background
    BG_FRAME = "#14171F"         # Frame/panel background
    BG_BUTTON = "#1E222C"        # Button default
    BG_BUTTON_HOVER = "#D9A441"  # Button hover (gold)
    BG_BUTTON_ACTIVE = "#B5832E" # Button pressed (darker gold)
    BG_INPUT = "#1E222C"         # Input fields
    BG_SELECTED = "#2A2D39"      # Selected items
    
    # Text colors
    TEXT_PRIMARY = "#F5F5F7"     # Main text
    TEXT_SECONDARY = "#A3A6B3"   # Subtitle/secondary text
    TEXT_DARK = "#050609"        # Text on gold background
    TEXT_SUCCESS = "#4CAF50"     # Success messages
    TEXT_WARNING = "#FF9800"     # Warning messages
    TEXT_ERROR = "#F44336"       # Error messages
    
    # Border colors
    BORDER_DEFAULT = "#2A2D39"
    BORDER_FOCUS = "#D9A441"
    
    # Accent colors
    ACCENT_GOLD = "#D9A441"
    ACCENT_GOLD_DARK = "#B5832E"
    
    # Fonts
    FONT_FAMILY = "Segoe UI"
    FONT_SIZE_SMALL = 10
    FONT_SIZE_NORMAL = 12
    FONT_SIZE_LARGE = 14
    FONT_SIZE_HEADER = 18
    FONT_SIZE_TITLE = 22
    
    @staticmethod
    def button_style():
        """Returns standard button styling"""
        return {
            'bg': Theme.BG_BUTTON,
            'fg': Theme.TEXT_PRIMARY,
            'font': (Theme.FONT_FAMILY, Theme.FONT_SIZE_LARGE, 'bold'),
            'relief': 'flat',
            'borderwidth': 1,
            'activebackground': Theme.BG_BUTTON_ACTIVE,
            'activeforeground': Theme.TEXT_DARK,
            'cursor': 'hand2'
        }
    
    @staticmethod
    def button_hover_style():
        """Returns hover button styling"""
        return {
            'bg': Theme.BG_BUTTON_HOVER,
            'fg': Theme.TEXT_DARK
        }
    
    @staticmethod
    def primary_button_style():
        """Returns primary/action button styling"""
        return {
            'bg': Theme.ACCENT_GOLD,
            'fg': Theme.TEXT_DARK,
            'font': (Theme.FONT_FAMILY, Theme.FONT_SIZE_LARGE, 'bold'),
            'relief': 'flat',
            'activebackground': Theme.ACCENT_GOLD_DARK,
            'activeforeground': Theme.TEXT_DARK,
            'cursor': 'hand2'
        }
    
    @staticmethod
    def label_style(size='normal', bold=False):
        """Returns label styling"""
        font_size = {
            'small': Theme.FONT_SIZE_SMALL,
            'normal': Theme.FONT_SIZE_NORMAL,
            'large': Theme.FONT_SIZE_LARGE,
            'header': Theme.FONT_SIZE_HEADER,
            'title': Theme.FONT_SIZE_TITLE
        }.get(size, Theme.FONT_SIZE_NORMAL)
        
        weight = 'bold' if bold else 'normal'
        
        return {
            'bg': Theme.BG_DARK,
            'fg': Theme.TEXT_PRIMARY,
            'font': (Theme.FONT_FAMILY, font_size, weight)
        }
    
    @staticmethod
    def secondary_label_style():
        """Returns secondary/subtitle label styling"""
        return {
            'bg': Theme.BG_DARK,
            'fg': Theme.TEXT_SECONDARY,
            'font': (Theme.FONT_FAMILY, Theme.FONT_SIZE_SMALL)
        }
    
    @staticmethod
    def entry_style():
        """Returns entry/input field styling"""
        return {
            'bg': Theme.BG_INPUT,
            'fg': Theme.TEXT_PRIMARY,
            'font': (Theme.FONT_FAMILY, Theme.FONT_SIZE_NORMAL),
            'relief': 'flat',
            'insertbackground': Theme.TEXT_PRIMARY,
            'highlightthickness': 2,
            'highlightbackground': Theme.BORDER_DEFAULT,
            'highlightcolor': Theme.BORDER_FOCUS
        }
    
    @staticmethod
    def frame_style():
        """Returns frame styling"""
        return {
            'bg': Theme.BG_FRAME,
            'relief': 'flat',
            'borderwidth': 0
        }
    
    @staticmethod
    def window_style():
        """Returns main window styling"""
        return {
            'bg': Theme.BG_DARK
        }

# Utility function to bind hover effects
def bind_hover_effect(widget, enter_config=None, leave_config=None):
    
    if enter_config is None:
        enter_config = Theme.button_hover_style()
    if leave_config is None:
        leave_config = {'bg': Theme.BG_BUTTON, 'fg': Theme.TEXT_PRIMARY}
    
    def on_enter(e):
        widget.config(**enter_config)
    
    def on_leave(e):
        widget.config(**leave_config)
    
    widget.bind("<Enter>", on_enter)
    widget.bind("<Leave>", on_leave)