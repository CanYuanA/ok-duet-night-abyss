from qfluentwidgets import FluentIcon
import time
import random

from ok import Logger, TaskDisabledException
from src.tasks.DNAOneTimeTask import DNAOneTimeTask
from src.tasks.CommissionsTask import CommissionsTask, Mission

logger = Logger.get_logger(__name__)


class AutoExpulsion(DNAOneTimeTask, CommissionsTask):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.icon = FluentIcon.FLAG
        self.description = "全自动"
        self.default_config.update({
            '随机游走': False,
            '任务超时时间': 120,
            '刷几次': 999,
        })
        self.config_description.update({
            '随机游走': '是否在任务中随机移动',
            '任务超时时间': '放弃任务前等待的秒数',
        })
        self.setup_commission_config()
        self.default_config.pop("启用自动穿引共鸣", None)
        self.name = "自动驱离"
        self.action_timeout = 10

    def run(self):
        DNAOneTimeTask.run(self)
        self.move_mouse_to_safe_position()
        try:
            return self.do_run()
        except TaskDisabledException as e:
            pass
        except Exception as e:
            logger.error("AutoExpulsion error", e)
            raise

    def do_run(self):
        self.load_char()
        _start_time = 0
        _skill_time = 0
        _random_walk_time = 0
        _count = 0
        while True:
            if self.in_team():
                if _start_time == 0:
                    _count += 1
                    self.move_on_begin()
                    _start_time = time.time()
                _skill_time = self.use_skill(_skill_time)
                _random_walk_time = self.random_walk(_random_walk_time)
                if time.time() - _start_time >= self.config.get("任务超时时间", 120):
                    logger.info("已经超时，重开任务...")
                    self.give_up_mission()
                    self.wait_until(lambda: not self.in_team(), time_out=30, settle_time=1)

            _status = self.handle_mission_interface()
            if _status == Mission.START:
                self.wait_until(self.in_team, time_out=30)
                if _count >= self.config.get("刷几次", 999):
                    self.sleep(1)
                    self.open_in_mission_menu()
                    self.log_info_notify("任务终止")
                    self.soundBeep()
                    return
                self.log_info("任务开始")
                self.sleep(2.5)
                _start_time = 0
            self.sleep(0.2)

    def move_on_begin(self):
        # 复位方案
        self.reset_and_transport()
        # 防卡墙
        self.send_key_down("w")
        self.sleep(0.5)
        self.send_key_up("w")

    def random_walk(self, last_time):
        duration = 1
        interval = 3
        if self.config.get("随机游走", False):
            if time.time() - last_time >= interval:
                direction = random.choice(["w", "a", "s", "d"])
                self.send_key(direction, down_time=duration)
                return time.time()
        return last_time

