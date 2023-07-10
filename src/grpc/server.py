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
from concurrent import futures
import time
import socket

import numpy as np
from proto.buffer_pb2 import *
from proto.buffer_pb2_grpc import *
from utils import *


def rd_buf():
    return BufferInfo(
        name=rd_str(1)[0],
        libcell=np.random.randint(0, high=10000),
        loc=Location(
            x=np.random.random_sample() * 1000, y=np.random.random_sample() * 1000
        ),
    )


def rd_buf_answer(num_bufs, num_edges):
    return NetAnswer(
        net_name=rd_str(1)[0],
        buffers=[rd_buf() for _ in range(num_bufs)],
        edges=[Edge(src=rd_str(1)[0], snk=rd_str(1)[0]) for _ in range(num_edges)],
    )


class BufFormerServicer(BufFormerServicer):
    def __init__(self):
        super(BufFormerServicer, self).__init__()
        self._rts = []
    
    def CallBufFormer(self, request, context):
        ...  # perform inference here
        num_nets = len(request.queries)
        tt = time.time()
        print(f"receiving {num_nets} net queries at timestamp = {time.time()}")
        num_bufs = np.random.randint(2, 7, size=num_nets)
        num_edges = np.random.randint(5, high=20, size=num_nets)
        answers = [rd_buf_answer(num_bufs[i], num_edges[i]) for i in range(num_nets)]
        rt = time.time() - tt
        print(f"generation of buffers took {rt}")
        self._rts.append(rt)
        print(f"mean generation time = {np.mean(self._rts)}")
        print(f"sending inferenced buffer insertion at timestamp = {time.time()}")
        return BatchAnswer(answers=answers)


def serve():
    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=2),
        maximum_concurrent_rpcs=100,
        options=[
            ("grpc.max_send_message_length", 1024 * 1024 * 1024),
            ("grpc.max_receive_message_length", 1024 * 1024 * 1024),
        ],
    )
    add_BufFormerServicer_to_server(BufFormerServicer(), server)
    server.add_insecure_port("[::]:50051")
    server.start()
    host = socket.gethostname()
    print(f"Server started at Host: {host}")
    server.wait_for_termination()


if __name__ == "__main__":
    serve()

