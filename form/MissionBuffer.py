import numpy as np



class MissionBuffer:
    def __init__(self, data=None):
        self.data_num = data.shape[1]
        self.data = data if data is not None else np.zeros((22, self.data_num))
        self.cur_idx = 0
        self.first_call = True


    def reset(self):
        self.first_call = True
        self.cur_idx = 0

    def get_cur_buffer(self):
        return self.data[:, self.cur_idx]

    def get_pre_buffer(self):
        if self.first_call:
            self.first_call = False
            return self.get_cur_buffer()
        self.cur_idx -= 1
        if self.cur_idx < 0:
            self.cur_idx = self.data_num - 1
            if self.cur_idx < 0:
                self.cur_idx = 0

        return self.get_cur_buffer()

    def get_next_buffer(self):
        if self.first_call:
            self.first_call = False
            return self.get_cur_buffer()

        self.cur_idx += 1
        if self.cur_idx >= self.data_num:
            self.cur_idx = 0

        return self.get_cur_buffer()

    def get_cur_idx(self):
        return self.cur_idx

    def get_buffer_data(self, i, j):
        return self.data[i, j]

