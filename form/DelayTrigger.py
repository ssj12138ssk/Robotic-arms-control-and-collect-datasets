class DelayTrigger:
    def __init__(self, delay_num=0):
        self.delay_num = delay_num
        self.count_down = -1

    def init(self, delay_num):
        self.delay_num = delay_num

    def update(self, val_input):
        if self.delay_num == 0:
            return val_input

        val_output = False
        if val_input and self.count_down == -1:
            self.count_down = self.delay_num

        if self.count_down >= 0:
            self.count_down -= 1

        if self.count_down == 0:
            val_output = True

        return val_output