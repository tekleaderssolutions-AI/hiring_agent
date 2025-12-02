"""
Helper function to find the first available date with free slots
"""
from datetime import datetime, timedelta
from google_calendar import get_available_slots

def find_first_available_date(num_slots=3, max_days_ahead=30):
    """
    Find the first date with available interview slots.
    
    Args:
        num_slots: Number of slots needed (default: 3)
        max_days_ahead: Maximum days to search ahead (default: 30)
    
    Returns:
        datetime object of first available date, or None if no date found
    """
    current_date = datetime.now() + timedelta(days=1)  # Start from tomorrow
    end_date = datetime.now() + timedelta(days=max_days_ahead)
    
    while current_date <= end_date:
        # Skip weekends
        if current_date.weekday() >= 5:  # Saturday = 5, Sunday = 6
            current_date += timedelta(days=1)
            continue
        
        try:
            slots = get_available_slots(current_date, num_slots)
            if len(slots) >= num_slots:
                return current_date
        except Exception as e:
            print(f"Error checking {current_date.date()}: {e}")
        
        current_date += timedelta(days=1)
    
    return None
