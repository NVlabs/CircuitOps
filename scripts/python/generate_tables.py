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

from openroad_helpers import get_tables_OpenROAD_API
import argparse, os


if __name__ == "__main__":
  parser = argparse.ArgumentParser(description="Options to store the IR tables as .csv files, give design name and tech node.")
  parser.add_argument("-w", default=True, action = 'store_true')
  parser.add_argument("-d", default="gcd", help="Give the design name")
  parser.add_argument("-t", default="nangate45", help="Give the technology node")
  args = parser.parse_args() 
   
  IRTables = get_tables_OpenROAD_API("./", args.w, True, args.d, args.t)
  os._exit(0)
  
