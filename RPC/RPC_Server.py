# encoding:utf-8
import json
import re
import traceback
from http import HTTPStatus
from xmlrpc.server import SimpleXMLRPCServer
from xmlrpc.server import SimpleXMLRPCRequestHandler
from Utils.log_utils import logger
from RPC import register_list


# Restrict to a particular path.

class RequestHandler(SimpleXMLRPCRequestHandler):
    def log_request(self, code='-', size='-'):
        """Selectively log an accepted request."""
        if self.server.logRequests:
            if isinstance(code, HTTPStatus):
                code = code.value
            logger.info('"%s" %s %s from %s',
                        self.requestline, str(code), str(size), self.client_address[0])


# Create server
import sys

# server = SimpleXMLRPCServer(("0.0.0.0", 9017))
server = SimpleXMLRPCServer(("0.0.0.0", 9017), requestHandler=RequestHandler,allow_none=True)
server.register_introspection_functions()

def ip_port_list(method_with_params_list,length=None):
    '''
    将非基本数据类型转成基本数据类型(_id)
    :param method_with_params_list:
    :param length:
    :return:
    '''
    data = to_list(method_with_params_list,length)
    for d in data:
        d['_id'] = str(d['_id'])
    return data

def to_list(method_with_params_list,length=None):
    '''

    :param method_with_params_list:
    :param length: 防止list过大导致传不了
    :return:
    '''
    return_data = list(run(method_with_params_list))
    return return_data[:length] if length else return_data

def run(method_with_params_list):
    '''
    代理方法，需要在全局维护一个registest_list
    :param method_with_params_list:
    :return:
    '''
    def do_chain(method, params_list, current_step):
        method_name = method.replace('()', '')
        # 判断有没有这属性
        if not hasattr(current_step, method_name):
            raise Exception('{0}没有属性{1}'.format(str(current_step), method_name))

        if re.findall(r'\(\)', method):  # 是方法
            this_params = params_list.pop(0)
            this_args = this_params['args']
            this_kwargs = this_params['kwargs']
            current_step = getattr(current_step, method_name)(*this_args, **this_kwargs)
        else:
            current_step = getattr(current_step, method_name)
        return current_step

    method = method_with_params_list[0]
    params_list = method_with_params_list[1]
    try:
        current_step = None
        logger.info('-------------------处理 {0}，参数：{1}'.format(method,params_list))
        first_method = method.split('.')[0]
        first_method_name = first_method.replace('()', '')
        # 判断是否已经注册该方法/类
        if not first_method_name in register_list:
            raise Exception('类/方法%s没有注册' % first_method_name)
        else:
            first_registed_method_or_obj = register_list[first_method_name]

        if re.findall(r'\(\)', first_method):  # 是方法
            this_params = params_list.pop(0)
            this_args = this_params['args']
            this_kwargs = this_params['kwargs']
            current_step = first_registed_method_or_obj(*this_args, **this_kwargs)
        else:  # 不是方法
            current_step = first_registed_method_or_obj

        for m in method.split('.')[1:]:
            current_step = do_chain(m, params_list, current_step)

        return current_step
    except Exception as e:
        logger.error('{0} -------------- {1}'.format(method, traceback.format_exc()))
        raise e

server.register_function(lambda : 'aaa',name='a')
server.register_function(to_list)
server.register_function(ip_port_list)
server.register_function(run)
server.register_multicall_functions()

try:
    server.serve_forever()
except KeyboardInterrupt:
    print("\nKeyboard interrupt received, exiting.")
    server.server_close()
    sys.exit(0)

# if __name__=="__main__":
#     print(ExampleService().currentTime().getCurrentTime())
