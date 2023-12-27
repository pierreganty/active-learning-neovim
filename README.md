# Active Learning Neovim

Python code connecting the active learning library [AALpy](https://github.com/DES-Lab/AALpy) with [Neovim](https://github.com/neovim/neovim) as the System Under Learning using the [pynvim](https://github.com/neovim/pynvim) Python Neovim remote API.

# Requirements

- [AALpy](https://github.com/DES-Lab/AALpy) 
- [Neovim](https://github.com/neovim/neovim) 
- [pynvim](https://github.com/neovim/pynvim)

# Conformance testing

You can also use AALpy as a conformance testing tool given a SUL and a Moore machine in dot format. 
Below is some lightly tested code. The class `NvimSUL(SUL):` is to take from `aalpy_neovim.py`.

```python
import pynvim 
from aalpy.base import SUL
from aalpy.oracles import RandomWMethodEqOracle
from aalpy.utils import load_automaton_from_file
import asyncio.log
asyncio.log.logger.setLevel("ERROR")

class NvimSUL(SUL):
[...]

# load existing model
previous_model = load_automaton_from_file('file.dot' , 'moore')

new_nvim_sul = NvimSUL()

# Be careful to use and reuse the same alphabets
eq_oracle = RandomWMethodEqOracle(alphabet=['l', '<C-g>', '<C-v>', 'c', ':', 'v', 'g', '<C-o>', 'r', '<Esc>', '<CR>', '<C-c>', '<C-\><C-n>'], sul=new_nvim_sul, walks_per_state=100, walk_len=10)

# attempt to find a cex
cex = eq_oracle.find_cex(previous_model)
if cex:
   # You can query NvimSUL and previous model to see the differance
   new_nvim_output = new_nvim_sul.query(cex)
   MooreSUL(previous_model).query(cex)
   print(cex)
else:
   print("No counterexample found")
```
