#
# PC-BASIC 3.23 - var.py
#
# Variable & array management
# 
# (c) 2013, 2014 Rob Hagemans 
#
# This file is released under the GNU GPL version 3. 
# please see text file COPYING for licence terms.
#

from operator import itemgetter

import error
import vartypes
from string_ptr import StringPtr
import state

byte_size = {'$': 3, '%': 2, '!': 4, '#': 8}

# data memory model: start of variables section
var_mem_start = 4720
# 'free memory' as reported by FRE
total_mem = 60300    

class StringSpace(object):
    """ String space is a table of strings accessible by their 2-byte pointers. """
    
    def __init__(self):
        """ Initialise empty string space. """
        self.strings = {}
    
    def retrieve(self, key):
        """ Retrieve a string by its 2-byte key. 3-byte memory sequences allowed, we take the pointer from it. """
        key = str(key)
        if len(key) in (2, 3):
            return self.strings[key[-2:]]
        else:
            raise KeyError('String key %s has wrong length.' % repr(key))    

    def copy_packed(self, key):
        """ Return a packedcopy of the string by its 2-byte key or 3-byte sequence. """
        return vartypes.pack_string(self.retrieve(key)[:])

    def store(self, string_buffer, address=None):
        """ Store a new string and return the 3-byte memory sequence. """
        if address == None:
            # find new string address
            state.basic_state.string_current -= len(string_buffer)
            address = state.basic_state.string_current + 1 
        key = str(vartypes.value_to_uint(address))
        if key in self.strings:
            raise KeyError('String key %s already defined.' % repr(key))
        self.strings[key] = string_buffer    
        return bytearray(chr(len(string_buffer)) + key)

    def address(self, key):
        """ Return the address of a given key. """
        return vartypes.uint_to_value(bytearray(key[-2:]))
        

def clear_variables(preserve_common=False, preserve_all=False, preserve_deftype=False):
    """ Reset and clear variables, arrays, common definitions and functions. """
    if not preserve_deftype:
        # deftype is not preserved on CHAIN with ALL, but is preserved with MERGE
        state.basic_state.deftype = ['!']*26
    if not preserve_all:     
        if preserve_common:
            # preserve COMMON variables (CHAIN does this)
            common, common_arrays = {}, {}
            for varname in state.basic_state.common_names:
                try:
                    common[varname] = state.basic_state.variables[varname]
                except KeyError: 
                    pass    
            for varname in state.basic_state.common_array_names:
                try:
                    common_arrays[varname] = state.basic_state.arrays[varname]
                except KeyError:
                    pass    
        else:
            # clear option base
            state.basic_state.array_base = None
            common = {}
            common_arrays = {}        
            # at least I think these should be cleared by CLEAR?
            state.basic_state.common_names = []
            state.basic_state.common_array_names = []
        # restore only common variables
        # this is a re-assignment which is not FOR-safe; but clear_variables is only called in CLEAR which also clears the FOR stack
        state.basic_state.variables = {}
        state.basic_state.arrays = {}
        state.basic_state.var_memory = {}
        state.basic_state.array_memory = {}
        state.basic_state.var_current = var_mem_start
        state.basic_state.string_current = state.basic_state.var_current + total_mem # 65020
        # arrays are always kept after all vars
        state.basic_state.array_current = 0
        # functions are cleared except when CHAIN ... ALL is specified
        state.basic_state.functions = {}
        # reset string space
        state.basic_state.strings = StringSpace()
        # preserve common variables
        # use set_var and dim_array to rebuild memory model
        for v in common:    
            set_var(v, (v[-1], common[v]))
        for a in common_arrays:
            dim_array(a, common_arrays[a][0])
            state.basic_state.arrays[a] = common_arrays[a]

# initialise the var module
clear_variables()


def set_var(name, value):
    """ Assign a value to a variable. """
    name = vartypes.complete_name(name)
    type_char = name[-1]
    # check if garbage needs collecting before allocating mem
    size = (max(3, len(name)) + 1 + byte_size[type_char])
    if type_char == '$':
        unpacked = vartypes.pass_string_unpack(value) 
        size += len(unpacked)
    if fre() <= size:
        # TODO: GARBTEST difference is because string literal is currently stored in string space, whereas GW stores it in code space.
        collect_garbage()
        if fre() <= size:
            raise error.RunError(7)
    # assign variables
    if type_char == '$':
        # every assignment to string leads to new pointer being allocated
        # TODO: string literals in programs have the var ptr point to program space.
        # TODO: field strings point to field buffer
        state.basic_state.variables[name] = state.basic_state.strings.store(bytearray(unpacked[:]))
    else:
        # make a copy of the value in case we want to use POKE on it - we would change both values otherwise
        # NOTE: this is an in-place copy - crucial for FOR!
        try:
            state.basic_state.variables[name][:] = vartypes.pass_type_keep(name[-1], value)[1][:]
        except KeyError:
            state.basic_state.variables[name] = vartypes.pass_type_keep(name[-1], value)[1][:]
    # update memory model
    # first two bytes: chars of name or 0 if name is one byte long
    if name not in state.basic_state.var_memory:
        name_ptr = state.basic_state.var_current
        var_ptr = name_ptr + max(3, len(name)) + 1 # byte_size first_letter second_letter_or_nul remaining_length_or_nul 
        state.basic_state.var_current += max(3, len(name)) + 1 + byte_size[name[-1]]
        state.basic_state.var_memory[name] = (name_ptr, var_ptr)
        
def get_var(name):
    """ Retrieve the value of a variable. """
    name = vartypes.complete_name(name)
    try:
        if name[-1] == '$':
            return state.basic_state.strings.copy_packed(state.basic_state.variables[name])
        else:
            return (name[-1], state.basic_state.variables[name])
    except KeyError:
        return vartypes.null[name[-1]]

def swap_var(name1, index1, name2, index2):
    """ Swap two variables by reference (Strings) or value (everything else). """
    if name1[-1] != name2[-1]:
        # type mismatch
        raise error.RunError(13)
    elif ((index1 == [] and name1 not in state.basic_state.variables) or 
            (index1 != [] and name1 not in state.basic_state.arrays) or 
            (index2 == [] and name2 not in state.basic_state.variables) or
            (index2 != [] and name2 not in state.basic_state.arrays)):
        # illegal function call
        raise error.RunError(5)
    typechar = name1[-1]
    size = byte_size[typechar]
    # swap non-strings by value, strings by address
    if index1 == []:
        p1, off1 = state.basic_state.variables[name1], 0
    else:
        dimensions, p1, _ = state.basic_state.arrays[name1]
        off1 = index_array(index1, dimensions)*size
    if index2 == []:
        p2, off2 = state.basic_state.variables[name2], 0
    else:
        dimensions, p2, _ = state.basic_state.arrays[name2]
        off2 = index_array(index2, dimensions)*size
    # swap the contents    
    p1[off1:off1+size], p2[off2:off2+size] =  p2[off2:off2+size], p1[off1:off1+size]  
    # inc version
    if name1 in state.basic_state.arrays:
        state.basic_state.arrays[name1][2] += 1
    if name2 in state.basic_state.arrays:
        state.basic_state.arrays[name2][2] += 1

def erase_array(name):
    """ Remove an array from memory. """
    try: 
        del state.basic_state.arrays[name]
    except KeyError:
        # illegal fn call
        raise error.RunError(5)    

def index_array(index, dimensions):
    """ Return the flat index for a given dimensioned index. """
    bigindex = 0
    area = 1
    for i in range(len(index)):
        # WARNING: dimensions is the *maximum index number*, regardless of state.basic_state.array_base!
        bigindex += area*(index[i]-state.basic_state.array_base)
        area *= (dimensions[i]+1-state.basic_state.array_base)
    return bigindex 
    
def array_len(dimensions):
    """ Return the flat length for given dimensioned size. """
    return index_array(dimensions, dimensions) + 1    

def var_size_bytes(name):
    """ Return the size of a variable, if it exists. Raise ILLEGAL FUNCTION CALL otherwise. """
    try:
        return byte_size[name[-1]]  
    except KeyError:
        raise error.RunError(5)

def array_size_bytes(name):
    """ Return the byte size of an array, if it exists. Return 0 otherwise. """ 
    try:
        dimensions, _, _ = state.basic_state.arrays[name]
    except KeyError:
        return 0
    return array_len(dimensions) * var_size_bytes(name)     

def dim_array(name, dimensions):
    """ Allocate array space for an array of given dimensioned size. Raise errors if duplicate name or illegal index value. """
    if state.basic_state.array_base == None:
        state.basic_state.array_base = 0
    name = vartypes.complete_name(name)
    if name in state.basic_state.arrays:
        # duplicate definition
        raise error.RunError(10)
    for d in dimensions:
        if d < 0:
            # illegal function call
            raise error.RunError(5)
        elif d < state.basic_state.array_base:
            # subscript out of range
            raise error.RunError(9)
    size = array_len(dimensions)
    try:
        state.basic_state.arrays[name] = [ dimensions, bytearray(size*var_size_bytes(name)), 0 ]  
    except OverflowError:
        # out of memory
        raise error.RunError(7) 
    except MemoryError:
        # out of memory
        raise error.RunError(7) 
    # update memory model
    # first two bytes: chars of name or 0 if name is one byte long
    name_ptr = state.basic_state.array_current
    record_len = 1 + max(3, len(name)) + 3 + 2*len(dimensions)
    array_ptr = name_ptr + record_len
    state.basic_state.array_current += record_len + array_size_bytes(name)
    state.basic_state.array_memory[name] = (name_ptr, array_ptr)

def check_dim_array(name, index):
    """ Check if an array has been allocated. If not, auto-allocate if indices are <= 10; raise error otherwise. """
    try:
        [dimensions, lst, _] = state.basic_state.arrays[name]
    except KeyError:
        # auto-dimension - 0..10 or 1..10 
        # this even fixes the dimensions if the index turns out to be out of range!
        dimensions = [ 10 ] * len(index)
        dim_array(name, dimensions)
        [dimensions, lst, _] = state.basic_state.arrays[name]
    if len(index) != len(dimensions):
        raise error.RunError(9)
    for i in range(len(index)):
        if index[i] < 0:
            raise error.RunError(5)
        elif index[i] < state.basic_state.array_base or index[i] > dimensions[i]: 
            # WARNING: dimensions is the *maximum index number*, regardless of state.basic_state.array_base!
            raise error.RunError(9)
    return [dimensions, lst]

def base_array(base):
    """ Set the array base to 0 or 1 (OPTION BASE). Raise error if already set. """
    if base not in (1, 0):
        # syntax error
        raise error.RunError(2)    
    if state.basic_state.array_base != None and base != state.basic_state.array_base: 
        # duplicate definition
        raise error.RunError(10)
    state.basic_state.array_base = base

def get_array(name, index):
    """ Retrieve the value of an array element. """
    [dimensions, lst] = check_dim_array(name, index)
    bigindex = index_array(index, dimensions)
    value = lst[bigindex*var_size_bytes(name):(bigindex+1)*var_size_bytes(name)]
    if name[-1] == '$':
        return state.basic_state.strings.copy_packed(value)
    return (name[-1], value)
    
def set_array(name, index, value):
    """ Assign a value to an array element. """
    [dimensions, lst] = check_dim_array(name, index)
    bigindex = index_array(index, dimensions)
    # make a copy of the value, we don't want them to be linked
    value = (vartypes.pass_type_keep(name[-1], value)[1])[:]
    # for strings, store the string in string space and store the key in the array
    if name[-1] == '$':
        value = state.basic_state.strings.store(bytearray(value))
    bytesize = var_size_bytes(name)
    lst[bigindex*bytesize:(bigindex+1)*bytesize] = value
    # inc version
    state.basic_state.arrays[name][2] += 1
    
def get_var_or_array(name, indices):
    """ Retrieve the value of a variable or an array element. """
    if indices == []:
        return get_var(name)            
    else:
        return get_array(name, indices)

def set_var_or_array(name, indices, value):
    """ Assign a value to a variable or an array element. """
    if indices == []:    
        set_var(name, value)
    else:
        set_array(name, indices, value)
        
        
def set_field_var(field, varname, offset, length):
    """ Attach a variable to a FIELD buffer. """
    if varname[-1] != '$':
        # type mismatch
        raise error.RunError(13)
    if offset+length > len(field):
        # FIELD overflow
        raise error.RunError(50)    
    str_ptr = StringPtr(field, offset, length)
    # FIXME: address for FIELDs not implemented. This is a hack to provide a key that works only if there's only one field and one var.
    str_addr = offset
    # assign the string ptr to the variable name
    # desired side effect: if we re-assign this string variable through LET, it's no longer connected to the FIELD.
    state.basic_state.variables[varname] = state.basic_state.strings.store(str_ptr, str_addr)
    # update memory model (see set_var)
    if varname not in state.basic_state.variables:
        name_ptr = state.basic_state.var_current
        var_ptr = name_ptr + max(3, len(varname)) + 1 # byte_size first_letter second_letter_or_nul remaining_length_or_nul 
        state.basic_state.var_current += max(3, len(varname)) + 1 + byte_size['$']
        state.basic_state.var_memory[varname] = (name_ptr, var_ptr)
    
def assign_field_var(varname, value, justify_right=False):
    """ Write a value into a field-assigned variable. """
    if varname[-1] != '$' or value[0] != '$':
        # type mismatch
        raise error.RunError(13)
    s = vartypes.unpack_string(value)
    try:
        el = len(state.basic_state.variables[varname].buffer)    
    except KeyError:
        return
    if len(s) > el:
        s = s[:el]
    if len(s) < el:
        if justify_right:
            s = ' '*(el-len(s)) + s
        else:
            s += ' '*(el-len(s))
    state.basic_state.variables[varname].set_value(s)    

##########################################

def collect_garbage():
    """ Collect garbage from string space. Compactify string storage. """
    string_list = []
    for name in state.basic_state.var_memory:
        if name[-1] == '$':
            mem = state.basic_state.var_memory[name]
            v = state.basic_state.variables[name]
            string_list.append( (name, mem[0], mem[1], v.address, len(v.buffer)) )
    # sort by str_ptr, largest first        
    string_list.sort(key=itemgetter(3), reverse=True)        
    new_string_current = var_mem_start + total_mem              
    for item in string_list:
        new_string_current -= item[4]
        # re-allocate string space; no need to copy buffer
        state.basic_state.variables[name] = state.basic_state.strings.store(v.buffer) 
        state.basic_state.var_memory[item[0]] = (item[1], item[2])     
    state.basic_state.string_current = new_string_current

def fre():
    """ Return the amount of memory available to variables, arrays, strings and code. """
    # NOTE this is in var.py because it's used by set_var. 
    # This can be avoided when we set var_mem_start correctly at the top of code space - e.g. use a parameter in clear_variables
    return state.basic_state.string_current - state.basic_state.var_current - state.basic_state.array_current - program_memory_size()
      
def program_memory_size():
    """ Return the size of the code buffer. """
    # NOTE this is in var.py because it's used by set_var through fre() 
    return len(state.basic_state.bytecode.getvalue()) - 3
    
def assert_variables_memory_size():
    """ Return the amount of memory used by variables and arrays but not string buffers. For debugging. """
    mem_used = 0
    for name in state.basic_state.variables:
        mem_used += 1 + max(3, len(name))
        # string length incorporated through use of state.basic_state.string_current
        mem_used += var_size_bytes(name)
    for name in state.basic_state.arrays:
        mem_used += 4 + array_size_bytes(name) + max(3, len(name))
        dimensions, lst, _ = state.basic_state.arrays[name]
        mem_used += 2*len(dimensions)    
    assert (mem_used == state.basic_state.var_current - var_mem_start + state.basic_state.array_current)
     
