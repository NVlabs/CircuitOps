# SPDX-FileCopyrightText: Copyright (c) 2022 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import grpc
import time
from proto.buffer_pb2 import *
from proto.buffer_pb2_grpc import *
from utils import *
import numpy as np


def rd_net_query(deg):
    net_name = rd_str(1)
    cell_names = rd_str(deg)
    libs = np.random.randint(0, high=10000, size=deg).astype("uint32")
    slews, capas, dlys = np.random.random_sample((3, deg))
    locs = np.random.random_sample((deg, 2)) * 1000
    drvs, prts = np.random.choice(a=[False, True], size=(2, deg))
    return NetQuery(
        net_name=net_name[0],
        tokens=[
            CellToken(
                name=cell_names[i],
                libcell=libs[i],
                input_slew=slews[i],
                input_capa=capas[i],
                loc=Location(x=locs[i][0], y=locs[i][1]),
                is_driver=drvs[i],
                delay_tgt=dlys[i],
                parity=prts[i],
            )
            for i in range(deg)
        ],
    )


def rd_nets(num_nets, min_deg=5, max_deg=11):
    degrees = np.random.randint(min_deg, high=max_deg, size=num_nets)
    queries = [rd_net_query(degrees[i]) for i in range(num_nets)]
    return BatchQuery(queries=queries)


class Client(object):
    def __init__(self, hostname: str, port:int = 50051):
        self.host = hostname
        self.port = port
        # start channel
        self.channel = grpc.insecure_channel(
            "{}:{}".format(self.host, self.port),
            options=[
                ("grpc.max_send_message_length", 1024 * 1024 * 1024),
                ("grpc.max_receive_message_length", 1024 * 1024 * 1024),
            ],
        )
        # bind the client and the server
        self.stub = BufFormerStub(self.channel)

    def insert_buffers(self, num_nets=7500):
        print(f"generating {num_nets} net queries at timestamp = {time.time()}")
        req = rd_nets(num_nets)
        tt = time.time()
        print(f"sending {num_nets} net queries at timestamp = {tt}")
        resp = self.stub.CallBufFormer(req)
        rt = time.time() - tt
        print(f"received inferenced buffer insertion after = {rt}")
        return resp, rt


if __name__ == "__main__":
    client = Client()
    rts = []
    for _ in range(100):
        resp, rt = client.insert_buffers()
        rts.append(rt)
    print(rts)
    print(np.mean(rts))

