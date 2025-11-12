import time
import numpy as np
import cv2
import winsound
import win32api, win32con
from datetime import datetime, timedelta

from ok import BaseTask, Box, Logger, PostMessageInteraction

logger = Logger.get_logger(__name__)

class BaseDNATask(BaseTask):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.key_config = self.get_global_config('Game Hotkey Config')  # 游戏热键配置
        self.monthly_card_config = self.get_global_config('Monthly Card Config')
        self.afk_config = self.get_global_config('挂机设置')
        self.old_mouse_pos = None
        self.next_monthly_card_start = 0

    def in_team(self) -> bool:
        if self.find_one('lv_text', threshold=0.8):
            return True
        return False
    
    def find_start_btn(self, threshold: float = 0, box: Box | None = None, template = None) -> Box | None:
        if isinstance(box, Box):
            self.draw_boxes(box.name, box, "blue")
        return self.find_one('start_icon', threshold=threshold, box=box, template=template)
    
    def find_cancel_btn(self, threshold: float = 0, box: Box | None = None, template = None) -> Box | None:
        if isinstance(box, Box):
            self.draw_boxes(box.name, box, "blue")
        return self.find_one('cancel_icon', threshold=threshold, box=box, template=template)
    
    def find_retry_btn(self, threshold: float = 0, box: Box | None = None, template = None) -> Box | None:
        if isinstance(box, Box):
            self.draw_boxes(box.name, box, "blue")
        return self.find_one('retry_icon', threshold=threshold, box=box, template=template)
    
    def find_quit_btn(self, threshold: float = 0, box: Box | None = None, template=None) -> Box | None:
        if isinstance(box, Box):
            self.draw_boxes(box.name, box, "blue")
        return self.find_one('quit_icon', threshold=threshold, box=box, template=template)
    
    def find_drop_item(self, rates = 2000, threshold: float = 0, box: Box | None = None, template = None) -> Box | None:
        if isinstance(box, Box):
            self.draw_boxes(box.name, box, "blue")
        return self.find_one(f'drop_item_{str(rates)}', threshold=threshold, box=box, template=template)

    def safe_get(self, key, default=None):
        if hasattr(self, key):
            return getattr(self, key)
        return default

    def soundBeep(self, _n=None):
        if hasattr(self, "config") and not self.config.get('发出声音提醒', True):
            return
        if _n is None:
            n = self.afk_config['提示音'] if self.afk_config['提示音'] > 0 else 1
        else:
            n = _n
        for _ in range(n):
            winsound.Beep(523, 150)
            self.sleep(0.3)

    def log_info_notify(self, msg):
        self.log_info(msg, notify=self.afk_config['弹出通知'])

    def move_mouse_to_safe_position(self):
        if self.afk_config["防止鼠标干扰"]:
            self.old_mouse_pos = win32api.GetCursorPos()
            abs_pos = self.executor.interaction.capture.get_abs_cords(self.width_of_screen(0.95), self.height_of_screen(0.6))
            win32api.SetCursorPos(abs_pos)
            self.sleep(0.02)

    def move_back_from_safe_position(self):
        if self.afk_config["防止鼠标干扰"] and self.old_mouse_pos is not None:
            self.sleep(0.02)
            win32api.SetCursorPos(self.old_mouse_pos)
            self.old_mouse_pos = None

    # def sleep(self, timeout):
    #     return super().sleep(timeout - self.check_for_monthly_card())

    def check_for_monthly_card(self):
        if self.should_check_monthly_card():
            self.handle_monthly_card()
            # start = time.time()
            # logger.info(f'check_for_monthly_card start check')
            # if self.in_combat():
            #     logger.info(f'check_for_monthly_card in combat return')
            #     return time.time() - start
            # if self.in_team():
            #     logger.info(f'check_for_monthly_card in team send sleep until monthly card popup')
            #     monthly_card = self.wait_until(self.handle_monthly_card, time_out=120, raise_if_not_found=False)
            #     logger.info(f'wait monthly card end {monthly_card}')
            #     cost = time.time() - start
            #     return cost
        return 0
    
    def should_check_monthly_card(self):
        if self.next_monthly_card_start > 0:
            if 0 < time.time() - self.next_monthly_card_start < 120:
                return True
        return False

    def set_check_monthly_card(self, next_day=False):
        if self.monthly_card_config.get('Check Monthly Card'):
            now = datetime.now()
            hour = self.monthly_card_config.get('Monthly Card Time')
            # Calculate the next 5 o'clock in the morning
            next_four_am = now.replace(hour=hour, minute=0, second=0, microsecond=0)
            if now >= next_four_am or next_day:
                next_four_am += timedelta(days=1)
            next_monthly_card_start_date_time = next_four_am - timedelta(seconds=30)
            # Subtract 1 minute from the next 5 o'clock in the morning
            self.next_monthly_card_start = next_monthly_card_start_date_time.timestamp()
            logger.info('set next monthly card start time to {}'.format(next_monthly_card_start_date_time))
        else:
            self.next_monthly_card_start = 0

    def handle_monthly_card(self):
        monthly_card = self.find_one('monthly_card', threshold=0.8)
        # self.screenshot('monthly_card1')
        ret = monthly_card is not None
        if ret:
            self.wait_until(self.in_team, time_out=10,
                            post_action=lambda: self.click_relative(0.50, 0.89, after_sleep=1))
            self.set_check_monthly_card(next_day=True)
        logger.debug(f'check_monthly_card {monthly_card}')
        return ret


lower_white = np.array([244, 244, 244], dtype=np.uint8)
lower_white_none_inclusive = np.array([243, 243, 243], dtype=np.uint8)
upper_white = np.array([255, 255, 255], dtype=np.uint8)
black = np.array([0, 0, 0], dtype=np.uint8)

def isolate_white_text_to_black(cv_image):
    """
    Converts pixels in the near-white range (244-255) to black,
    and all others to white.
    Args:
        cv_image: Input image (NumPy array, BGR).
    Returns:
        Black and white image (NumPy array), where matches are black.
    """
    match_mask = cv2.inRange(cv_image, black, lower_white_none_inclusive)
    output_image = cv2.cvtColor(match_mask, cv2.COLOR_GRAY2BGR)

    return output_image
