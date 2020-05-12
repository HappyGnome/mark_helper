# -*- coding: utf-8 -*-
"""
Created on Tue May 12 11:27:32 2020

@author: Ben
"""
import json

import logging


import LogHelper

logger = logging.getLogger(__name__)

class Config:
    '''
    Manage a dictionary of configuration options, including loading, saving
    and user modification via the command line
    '''
    def __init__(self, filepath="Default.cfg"):

        '''
        {'category_name':{'property_name':value}}
        '''
        self._categories = {}
        '''
        {'category_name':{'property_name':[type, prompt_string]}}
        '''
        self._meta = {}

        '''
        filepath for config file
        '''
        self.path = filepath

    def add_category(self, category):
        '''
        Add category to this config
        Does nothing if category exists

        Parameters
        ----------
        category : str
             name of category to add
        Returns
        -------
        None

        '''
        if not category in self._categories:
            self._categories[category] = {}
            self._meta[category] = {}

    def add_property(self, category, prop_name, **kwargs):
        '''
        Add property to this config

        Parameters
        ----------
        category : str
             name of category in which to add property
        prop_name : str
             name of property
        kwargs :
            value : match return of vartype
                initial value of the property
            prompt : str
                string to prompt user for this property
            vartype : unary function str -> type
                converts user input to stored value
        Returns
        -------
        None

        '''
        value = kwargs.get('value', '')
        prompt = kwargs.get('prompt', prop_name+': ')
        vartype = kwargs.get('vartype', str)
        if not prop_name in self._categories[category]:
            self._categories[category][prop_name] = value
            self._meta[category][prop_name] = [vartype, prompt]

    def set_property(self, category, prop_name, value):
        '''
        Set property for this config

        Parameters
        ----------
        category : str
             name of category in which to set property
        prop_name : str
             name of property
        value : match return of vartype
            value to set for the property
        Returns
        -------
        None

        Raises
        ------
        ValueError : if property does not exist

        Any raised by trying to convert value to associated vartype

        '''
        if category in self._categories and prop_name \
                                                in self._categories[category]:
            self._categories[category][prop_name] = \
                self._meta[category][prop_name][0](value)
        else: raise ValueError("Property {} not found in {}"
                               .format(prop_name, category))

    def get_property(self, category, prop_name):
        '''
        Get property for this config

        Parameters
        ----------
        category : str
             name of category in which to set property
        prop_name : str
             name of property
        Returns
        -------
        Value of the property found

        Raises
        ------
        ValueError : if property does not exist

        '''
        if category in self._categories and prop_name \
                                                in self._categories[category]:
            return self._categories[category][prop_name]
        raise ValueError("Property {} not found in {}"
                         .format(prop_name, category))


    def load(self):
        """
        Update config data from self.path (a json file)

        Properties not already present are ignored

        Returns
        -------
        None.

        """
        with open(self.path, "r") as config_file:
            full = json.load(config_file)
            for sec in self._categories:#update each section from full
                for prop in self._categories[sec]:
                    if sec in full and prop in full[sec]:
                        self._categories[sec][prop] = full[sec][prop]


    def cmd_config(self, args, gethelp=False):
        '''
        Command line method to prompt user to set a section or all of config

        Parameters
        ----------
        args : string list
            ['all'] or ['<sec name>']
        gethelp : bool, optional
            return help strings instead
            The default is False.

        Returns
        -------
        bool :
            True unless CLI should quit.

        '''
        if gethelp:
            dets = "Use \'config all\' or \'config <section>\' with <section> being:"
            for sec in self._categories:
                dets = dets+"\n\t"+sec
            return ["Edit current configuration", dets+"\nConfiguration options you are"+\
                    " prompted for can be left blank to keep the current setting."]


        if len(args) < 1 or not (args[0] in self._categories or args[0] == 'all'):
            print("Config section not found. "+self.cmd_config([], True)[1])#help text
            return True
        for cat in self._categories:
            if args[0] == cat or args[0] == 'all':
                for key in self._categories[cat]:
                    self._get_cfg_var(cat, key, self._meta[cat][key][1],
                                      self._meta[cat][key][0])

        try:
            with open(self.path, "w") as config_file:
                json.dump(self._categories, config_file)
        except (OSError, TypeError, ValueError):
            LogHelper.print_and_log(logger, "Warning: Config not saved!")
        return True


    def _get_cfg_var(self, sec, config_key, msg, vartype=str):
        '''
        Set variable in this config based on user input.

        Parameters
        ----------
        sec : str
            category of property to prompt for
        config_key : str
            property to prompt for
        vartype : unary function str -> type
            converts user input to stored value


        Return
        ------
        None
        '''
        try:
            inp = input(msg)
            if inp: #bump down to defaults etc
                self._categories[sec][config_key] = vartype(inp)
                return
        except ValueError:
            pass
        print("\tRemains: "+str(self._categories[sec][config_key]))
