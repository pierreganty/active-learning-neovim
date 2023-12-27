import pynvim # the Python client for Neovim
from aalpy.base import SUL
from aalpy.oracles import StatePrefixEqOracle # Oracle for equivalence queries
from aalpy.learning_algs import run_Lstar, run_KV
from aalpy.utils import save_automaton_to_file
from random import seed
seed(100)  # all experiments will be reproducible

# To silence warnings from pynvim 0.5.0, to be removed when https://github.com/neovim/pynvim/issues/555 is resolved
import asyncio.log
asyncio.log.logger.setLevel("ERROR")


class NvimSUL(SUL):
    """
    System under learning for Moore machine
    """

    def __init__(self):
        super().__init__()
        self.n = None
        self.reset()

    def reset(self):
        if self.n is not None:
            self.n.close()

        self.n = pynvim.attach("child", argv=['./nvim', '-u', 'NONE', '-i', 'NONE', '-n', '--embed', '--headless', 'DeleteMeAALpyFile.txt']) # -n : no swap file, -u,-i NONE : no config, we use a dummy filename to avoid error on write.
        # In order to get the Moore machine we need to 'configure' Neovim so as to "force" the behavior of its internal state into a finite state machine.    
        self.n.lua.vim.api.nvim_set_keymap('n', '<C-i>', '', {}) # Else not a state machine (result depends on jumplist)
        self.n.lua.vim.api.nvim_set_keymap('n', '<C-o>', '', {}) # Else not a state machine (result depends on jumplist)
        # The next two are preventing a too large state machine since the state remembers the state of the last visual selection (charwise, linewise or blockwise). Disabling the mapping still gives you a state machine but too large for now. It basically halved the number of states
        self.n.lua.vim.api.nvim_set_keymap('n', 'gv', 'v', {}) # Else not the state machine we would like to see (result of last visual selection :help gv depends on the history in keys entered)
        self.n.lua.vim.api.nvim_set_keymap('x', 'gv', '', {}) # Else not the state machine we would like to see (result of last visual selection :help gv depends on the history in keys entered), NOTE: 'x' means Visual but not select
        # In insert mode we do not want to insert anything in the buffer for otherwise we don't get a finite state machine since the result of some commands depends on the buffer content (e.g. c/bla)
        self.n.lua.vim.api.nvim_set_keymap('i', '$', '', {}) # Else not a state machine
        self.n.lua.vim.api.nvim_set_keymap('i', '/', '', {}) # Else not a state machine
        self.n.lua.vim.api.nvim_set_keymap('i', '0', '', {}) # Else not a state machine
        self.n.lua.vim.api.nvim_set_keymap('i', ':', '', {}) # Else not a state machine
        self.n.lua.vim.api.nvim_set_keymap('i', '<CR>', '', {}) # Else not a state machine
        self.n.lua.vim.api.nvim_set_keymap('i', 'c', '', {}) # Else not a state machine
        self.n.lua.vim.api.nvim_set_keymap('i', 'g', '', {}) # Else not a state machine
        self.n.lua.vim.api.nvim_set_keymap('i', 'h', '', {}) # Else not a state machine
        self.n.lua.vim.api.nvim_set_keymap('i', 'l', '', {}) # Else not a state machine
        self.n.lua.vim.api.nvim_set_keymap('i', 'r', '', {}) # Else not a state machine
        self.n.lua.vim.api.nvim_set_keymap('i', 'v', '', {}) # Else not a state machine
        self.n.lua.vim.api.nvim_set_keymap('i', 'w', '', {}) # Else not a state machine


        self.n.lua.vim.api.nvim_set_keymap('o', '/$', '', {}) # Else not a state machine (why?? it is a move that depends on the buffer content and can be extended. `/$` is not the same as `/$w` )
        self.n.lua.vim.api.nvim_set_keymap('c', ':', '', {}) # Else (e.g. ::g equals :g)
        self.n.lua.vim.api.nvim_set_keymap('c', '<C-g>', '', {}) # Else (can run : which returns, "E492: Not an editor command")
        self.n.lua.vim.api.nvim_set_keymap('c', '<C-o>', '', {}) # Else (can run : which returns, "E492: Not an editor command")
        self.n.lua.vim.api.nvim_set_keymap('c', '<C-v>', '', {}) # Else we can still insert `w`, `i`, `c` …
        self.n.lua.vim.api.nvim_set_keymap('c', 'c', '', {}) # ibid (can run :change)
        self.n.lua.vim.api.nvim_set_keymap('c', 'g', '', {}) # Else (can run :global also :gr that is grep)
        self.n.lua.vim.api.nvim_set_keymap('c', 'h', '', {}) # Else (can run :help)
        self.n.lua.vim.api.nvim_set_keymap('c', 'i', '', {}) # Else can run :i (remains a state machine but with lots of garbage) 
        self.n.lua.vim.api.nvim_set_keymap('c', 'l', '', {}) # Else (can run :list)
        self.n.lua.vim.api.nvim_set_keymap('c', 'r', '', {}) # Else (can run :read also :gr that is grep)
        self.n.lua.vim.api.nvim_set_keymap('c', 'v', '', {}) # Else (can run :vglobal) 
        self.n.lua.vim.api.nvim_set_keymap('c', 'w', '', {}) # Else (can run :write) not a state machine because return value depends whether a file exists or not
        self.n.lua.vim.api.nvim_set_keymap('n', 'r<C-v>', '', {}) # Else we can still replace with Special character in decimal using r<C-v>000 which makes the machine unnecessarily larger
        self.n.lua.vim.api.nvim_set_keymap('l', '/$', '', {}) # to make my life easier (language mapping). Might not be needed anymore
        self.n.api.set_option('cmdheight', 2)    # because of more-prompts IIRC
        self.n.api.set_option('complete', 'k/dev/null') # For completion <C-n> (or more surprisingly <C-v><C-\><C-n>) to look for words in /dev/null
        # (See https://neovim.io/doc/user/insert.html#i_CTRL-V because it looks like "The characters typed right after CTRL-V are not considered for mapping."
        self.n.api.set_option('shortmess', 'filnxtToOsWAIcqFSI') # Added by Vigoux
        self.n.api.set_option('showcmd', False)
        self.n.api.set_option('showmode', False) # https://github.com/neovim/neovim/issues/19352#issuecomment-1183200652
        self.n.api.set_option('timeout' , False) # Added by Vigoux
        self.n.api.set_option('ttimeout', False) # Added by Vigoux
        self.n.api.set_option('writeany', True)  # To avoid 'file already exists' message


    def cast_mode(mode):
        cast_mode = {
                'n': 'Normal',
                'no': 'Operator-pending',
                'nov': 'Operator-pending charwise',
                'noV': 'Operator-pending linewise',
                'no\x16': 'Operator-pending blockwise',
                'niI': 'Insert Normal (insert)',
                'niR': 'Replace Normal (replace)',
                'niV': 'Virtual Replace Normal',
                'nt': 'Normal in terminal-emulator',
                'v': 'Visual',
                'vs': 'Select Visual',
                'V': 'Visual Line',
                'Vs': 'Select Visual Line',
                '\x16': 'Visual Block',
                '\x16s': 'Select Visual Block',
                's': 'Select',
                'S': 'Select Line',
                '\x13': 'Select Block',
                'i': 'Insert',
                'ic': 'Insert Command-line completion',
                'ix': 'Insert Ctrl-X Mode',
                'R': 'Replace',
                'Rc': 'Replace Command-line completion',
                'Rx': 'Replace Ctrl-X Mode',
                'Rv': 'Virtual Replace',
                'Rvc': 'Virtual Replace mode completion',
                'c': 'Command-line editing',
                'cv': 'Ex mode',
                'r': 'Hit-enter prompt',
                'rm': 'The more prompt',
                't': 'Terminal mode'
                }
        return cast_mode[mode["mode"]] + (' waiting for input (blocking)' if mode["blocking"] else '')


    def pre(self):
        # Asserts that the new nvim process starts in 'Normal' mode
        assert self.mode()["mode"] == "n"

    def mode(self):
        return self.n.api.get_mode()

    def feed(self, keys):
        return self.n.input(keys)

    def post(self):
        # Tear down the nvim process, the Neovim devs answered on the matrix channel it is the only way to get a fresh clean instance.
        self.reset()

    def step(self, letter):
        if letter is not None:
            self.feed(letter)
        xxx = self.n.api.get_mode()
        next_mode = NvimSUL.cast_mode(xxx)
        return next_mode

# WL = 10 because we empirically measured that the diameter of generated Moore machine never exceeds 9 
# WPS = 300 for no particularly good reason. It seemed 'enough'.
def run_learning_for_vim(learning_algorithm, input_al=['l', '<C-g>', '0', '<C-v>', 'c', ':', 'v', 'g', '<C-o>', 'r', '<Esc>', '<CR>', '<C-c>', '<C-\><C-n>'], WPS = 300, WL = 10):
    assert learning_algorithm == 'KV' or learning_algorithm == 'L_star'
    sul = NvimSUL()
    state_origin_eq_oracle = StatePrefixEqOracle(
    input_al, sul, walks_per_state=WPS, walk_len=WL)
    if learning_algorithm == 'L_star' :
        print('Lstar')
        learned_moore = run_Lstar(input_al, sul, state_origin_eq_oracle, cex_processing='rs',
                                closing_strategy='single', automaton_type='moore', cache_and_non_det_check=True, print_level=2)
    
    # AALpy recommends KV over Lstar since release 1.4.0 (see the README file and also https://github.com/DES-Lab/AALpy/issues/43#issuecomment-1441909285)
    elif learning_algorithm == 'KV' :
        print('KV')
        learned_moore = run_KV(input_al, sul, state_origin_eq_oracle, cex_processing='rs',
                                automaton_type='moore', cache_and_non_det_check=True, print_level=3)
    file_path = 'nvim' + '_' + learning_algorithm + '_' + str(WPS) + '_' + str(WL)
    save_automaton_to_file(learned_moore, path=file_path, file_type='dot')
    return [learned_moore, file_path]


learned_automata_KV = run_learning_for_vim(learning_algorithm='KV')
