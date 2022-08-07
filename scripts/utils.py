"""
FedSim cli Utils
----------------
"""
import importlib.util
import inspect
import os
from collections import namedtuple
from typing import Tuple

import click
import yaml
from functools import partial

from fedsim.utils import get_from_module


def parse_class_from_file(s: str) -> object:
    f, c = s.split(":")
    path = f + ".py"
    if os.path.exists(path):
        spec = importlib.util.spec_from_file_location(
            os.path.dirname(path).replace(os.sep, "."),
            path,
        )

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return getattr(module, c)

    return None


def get_definition(name, modules):
    if not isinstance(modules, list):
        modules = [
            modules,
        ]

    if ":" in name:
        definition = parse_class_from_file(name)
    else:
        for module in modules:
            definition = get_from_module(
                module,
                name,
            )
            if definition is not None:
                break
    if definition is None:
        raise Exception(f"{definition} is not defined!")
    return definition


def get_context_pool(
    context,
    cls_pfx_tuple,
):
    ClassContext = namedtuple("ClassContext", ["cls", "prefix", "arg_dict"])
    context_pool = list()
    for cls, pfx in cls_pfx_tuple:
        context_pool.append(ClassContext(cls, pfx, dict()))

    def add_arg(key, value, prefix):
        context = list(filter(lambda x: x.prefix == prefix, context_pool))
        if len(context) == 0:
            raise Exception("{} is an invalid argument".format(key))
        else:
            context = context[0]
        if key in inspect.signature(context.cls).parameters.keys():
            context.arg_dict[key] = yaml.safe_load(value)
        else:
            raise Exception(
                "{} is not an argument of {}".format(key, context.cls.__name__)
            )

    i = 0
    while i < len(context.args):
        if context.args[i][:2] != "--":
            raise Exception("unexpected option {}".format(context.args[i]))
        if context.args[i][2] == "-":
            raise Exception(
                "option {} is not valid. No option should starts with ---".format(
                    context.args[i]
                )
            )
        prefix = context.args[i][2:4]
        arg = context.args[i][4:]
        arg = arg.replace("-", "_")
        if i == len(context.args) - 1 or context.args[i + 1][:2] == "--":
            add_arg(arg, "True", prefix)
            i += 1
        else:
            next_arg = context.args[i + 1]
            add_arg(arg, next_arg, prefix)
            i += 2
    return context_pool


# credit goes to
# https://stackoverflow.com/questions/48391777/nargs-equivalent-for-options-in-click
class OptionEatAll(click.Option):
    def __init__(self, *args, **kwargs):
        self.save_other_options = kwargs.pop("save_other_options", True)
        nargs = kwargs.pop("nargs", -1)
        assert nargs == -1, "nargs, if set, must be -1 not {}".format(nargs)
        super(OptionEatAll, self).__init__(*args, **kwargs)
        self._previous_parser_process = None
        self._eat_all_parser = None

    def add_to_parser(self, parser, ctx):
        def parser_process(value, state):
            # method to hook to the parser.process
            done = False
            value = [value]
            if self.save_other_options:
                # grab everything up to the next option
                while state.rargs and not done:
                    for prefix in self._eat_all_parser.prefixes:
                        if state.rargs[0].startswith(prefix):
                            done = True
                    if not done:
                        value.append(state.rargs.pop(0))
            else:
                # grab everything remaining
                value += state.rargs
                state.rargs[:] = []
            value = tuple(value)

            # call the actual process
            self._previous_parser_process(value, state)

        retval = super(OptionEatAll, self).add_to_parser(parser, ctx)
        for name in self.opts:
            our_parser = parser._long_opt.get(name) or parser._short_opt.get(name)
            if our_parser:
                self._eat_all_parser = our_parser
                self._previous_parser_process = our_parser.process
                our_parser.process = parser_process
                break
        return retval


def decode_margs(obj_and_args: Tuple):
    obj_and_args = list(obj_and_args)
    # local definition
    if any([len(i) > 1 for i in obj_and_args]):
        obj_name = obj_and_args.pop(0)
        obj_arg_list = obj_and_args
        obj = obj_name
    # included definitions
    else:
        obj = "".join(obj_and_args)
        obj_arg_list = []

    obj_args = dict()
    while len(obj_arg_list) > 0:
        arg = obj_arg_list.pop(0)
        if ":" in arg:
            key, val = arg.split(":")
            obj_args[key] = yaml.safe_load(val)
        else:
            raise Exception(f"{arg} is invalid argument!")

    return obj, obj_args

def ingest_fed_context(
    data_manager,
    algorithm,
    model,
    optimizer,
    local_optimizer,
    lr_scheduler,
    local_lr_scheduler,
    r2r_local_lr_scheduler, 
):
    # decode
    data_manager, data_manager_args = decode_margs(data_manager)
    algorithm, algorithm_args = decode_margs(algorithm)
    model, model_args = decode_margs(model)
    optimizer, optimizer_args = decode_margs(optimizer)
    local_optimizer, local_optimizer_args = decode_margs(local_optimizer)
    lr_scheduler, lr_scheduler_args = decode_margs(lr_scheduler)
    local_lr_scheduler, local_lr_scheduler_args = decode_margs(local_lr_scheduler)
    r2r_local_lr_scheduler, r2r_local_lr_scheduler_args = decode_margs(
        r2r_local_lr_scheduler
    )
    # find class defs
    data_manager_class = get_definition(
        name=data_manager,
        modules="fedsim.distributed.data_management",
    )
    algorithm_class = get_definition(
        name=algorithm,
        modules=[
            "fedsim.distributed.centralized.training",
            "fedsim.distributed.decentralized.training",
        ],
    )
    model_class = get_definition(
        name=model,
        modules="fedsim.models",
    )
    optimizer_class = get_definition(
        name=optimizer,
        modules="torch.optim",
    )
    local_optimizer_class = get_definition(
        name=local_optimizer,
        modules="torch.optim",
    )
    lr_scheduler_class = get_definition(
        name=lr_scheduler,
        modules="torch.optim.lr_scheduler",
    )
    local_lr_scheduler_class = get_definition(
        name=local_lr_scheduler,
        modules="torch.optim.lr_scheduler",
    )
    r2r_local_lr_scheduler_class = get_definition(
        name=r2r_local_lr_scheduler,
        modules="fedsim.lr_schedulers",
    )
    # raise if algorithm parent signature is overwritten (allow only hparam args)
    grandpa = inspect.getmro(algorithm_class)[-2]
    grandpa_args = set(inspect.signature(grandpa).parameters.keys())
    for alg_arg in algorithm_args:
        if alg_arg in grandpa_args:
            raise Exception(
                f"Not allowed to change parameters of {grandpa} which is "
                f"the parent of algorithm class {algorithm_class}." 
                "Check other cli options")
    # customize defs
    data_manager_class = partial(data_manager_class, **data_manager_args)
    algorithm_class = partial(algorithm_class, **algorithm_args)
    model_class = partial(model_class, **model_args)
    optimizer_class = partial(optimizer_class, **optimizer_args)
    local_optimizer_class = partial(local_optimizer_class, **local_optimizer_args)
    lr_scheduler_class = partial(lr_scheduler_class, **lr_scheduler_args)
    local_lr_scheduler_class = partial(
        local_lr_scheduler_class,
        **local_lr_scheduler_args,
    )
    r2r_local_lr_scheduler_class = partial(
        r2r_local_lr_scheduler_class,
        **r2r_local_lr_scheduler_args,
    )
    cfg = dict(
            data_manager=data_manager,
            algorithm=algorithm,
            model=model,
            optimizer=optimizer,
            local_optimizer=local_optimizer,
            lr_scheduler=lr_scheduler,
            local_lr_scheduler=local_lr_scheduler,
            r2r_local_lr_scheduler=r2r_local_lr_scheduler,

            data_manager_args = data_manager_args,
            algorithm_args=algorithm_args,
            model_args=model_args,
            optimizer_args=optimizer_args,
            local_optimizer_args=local_optimizer_args,
            lr_scheduler_args=lr_scheduler_args,
            local_lr_scheduler_args=local_lr_scheduler_args,
            r2r_local_lr_scheduler_args=r2r_local_lr_scheduler_args,

        )

    return (
        cfg,
        data_manager_class,
        algorithm_class,
        model_class,
        optimizer_class,
        local_optimizer_class,
        lr_scheduler_class,
        local_lr_scheduler_class,
        r2r_local_lr_scheduler_class,
    )
