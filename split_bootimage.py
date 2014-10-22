#! /bin/env python

######################################################################
#
#   File          : split_bootimg.py
#   Author(s)     : William Enck <enck@cse.psu.edu>
#   		    Ray Soong <ray_errt@hotmail.com>
#   Description   : Split appart an Android boot image created 
#                   with mkbootimg. The format can be found in
#                   android-src/system/core/mkbootimg/bootimg.h
#
#                   Thanks to alansj on xda-developers.com for 
#                   identifying the format in bootimg.h and 
#                   describing initial instructions for splitting
#                   the boot.img file.
#
#   Last Modified : Tue Dec  2 23:36:25 EST 2008
#   By            : William Enck <enck@cse.psu.edu>
#
#   Copyright (c) 2008 William Enck
#
######################################################################
import gzip
import os
import string
import struct
import sys
######################################################################
## Global Variables and Constants
SCRIPT = sys.argv[0]

PAGE_SIZE = 0
KERNEL_SIZE = 0
RAMDISK_SIZE =  0
SECOND_SIZE = 0

# Constants (from bootimg.h)
BOOT_MAGIC = 'ANDROID!'
BOOT_MAGIC_SIZE = 8
BOOT_NAME_SIZE = 16
BOOT_ARGS_SIZE = 512

# Unsigned integers are 4 bytes
UNSIGNED_SIZE = 4
######################################################################
def goto_exit(errorinfo):
	print "Error:%s" %errorinfo
	sys.exit(1)
######################################################################
## Supporting Subroutines
'''
=header_format (from bootimg.h)
struct boot_img_hdr
{
    unsigned char magic[BOOT_MAGIC_SIZE];

    unsigned kernel_size;  /* size in bytes */
    unsigned kernel_addr;  /* physical load addr */

    unsigned ramdisk_size; /* size in bytes */
    unsigned ramdisk_addr; /* physical load addr */

    unsigned second_size;  /* size in bytes */
    unsigned second_addr;  /* physical load addr */

    unsigned tags_addr;    /* physical addr for kernel tags */
    unsigned page_size;    /* flash page size we assume */
    unsigned unused[2];    /* future expansion: should be 0 */

    unsigned char name[BOOT_NAME_SIZE]; /* asciiz product name */

    unsigned char cmdline[BOOT_ARGS_SIZE];

    unsigned id[8]; /* timestamp / checksum / sha1 / etc */
};
'''
def parse_header(fn):
	
	global PAGE_SIZE
	global KERNEL_SIZE
	global RAMDISK_SIZE
	global SECOND_SIZE

	global UNSIGNED_SIZE
		
	INF = open(fn, 'rb')
	try:
		# Read the Magic
		buf = INF.read(BOOT_MAGIC_SIZE)
	    	if (buf != BOOT_MAGIC):
			print "Android Magic not found in %s. Giving up.\n" %fn
			sys.exit(1)
		
   		# Read kernel size and address (assume little-endian)
		buf = INF.read(UNSIGNED_SIZE * 2)
		k_size = struct.unpack("I", buf[:UNSIGNED_SIZE])[0]
		k_addr = struct.unpack("I", buf[UNSIGNED_SIZE:])[0]

    		# Read ramdisk size and address (assume little-endian)
		buf = INF.read(UNSIGNED_SIZE * 2)
		r_size = struct.unpack("I", buf[:UNSIGNED_SIZE])[0]
		r_addr = struct.unpack("I", buf[UNSIGNED_SIZE:])[0]

	    	# Read second size and address (assume little-endian)
		buf = INF.read(UNSIGNED_SIZE * 2)
		s_size = struct.unpack("I", buf[:UNSIGNED_SIZE])[0]
		s_addr = struct.unpack("I", buf[UNSIGNED_SIZE:])[0]

		# Ignore tags_addr
    		buf = INF.read(UNSIGNED_SIZE)

    		# get the page size (assume little-endian)
    		buf = INF.read(UNSIGNED_SIZE)
		p_size = struct.unpack("I", buf)[0]

    		# Ignore unused
		buf = INF.read(UNSIGNED_SIZE)
		buf = INF.read(UNSIGNED_SIZE)

    		# Read the name (board name)
    		buf = INF.read(BOOT_NAME_SIZE)
    		name = buf

    		# Read the command line
		buf = INF.read(BOOT_ARGS_SIZE)
		cmdline = buf

		# Ignore the id
		buf = INF.read(UNSIGNED_SIZE * 8)

    		# Print important values
    		print "Page size: %d (0x%08x)" %(p_size, p_size)
    		print "Kernel size: %d (0x%08x)" %(k_size, k_size)
    		print "Kernel address: %d (0x%08x)" %(k_addr, k_addr)
    		print "Ramdisk size: %d (0x%08x)" %(r_size, r_size)
    		print "Ramdisk address: %d (0x%08x)" %(r_addr, r_addr)
    		print "Second size: %d (0x%08x)" %(s_size, s_size)
    		print "Board name: %s" %(name)
    		print "Command line: %s" %(cmdline)

    		# Save the values
    		PAGE_SIZE = p_size
    		KERNEL_SIZE = k_size
    		RAMDISK_SIZE = r_size
    		SECOND_SIZE = s_size

	except IOError:
		goto_exit("Open %s Failed!" %fn)
	finally:
    		# Close the file
		INF.close()
######################################################################
#Function for Writing eKernel Ramdisk and Second
def dump_file(infn, outfn, offset, size):
	buf =  None
	with open(infn, 'rb') as INF:
		INF.seek(offset, 0)
		buf = INF.read(size)

	with open(outfn, 'wb') as OUTF:
		OUTF.write(buf)
######################################################################
def gunzip_file(infn, outfn):
	try:
		INF = gzip.open(infn, 'rb')	
		OUTF = open(outfn, 'wb')
		OUTF.write(INF.read())
		OUTF.close()
		INF.close()
	except Exception:
		goto_exit("Gunzip %s to %s Failed!" %(infn, outfn))
######################################################################
## Configuration Subroutines
def parse_cmdline():
	global SCRIPT
	global IMAGE_FN
	if len(sys.argv) < 2:
		print "Usage: %s boot.img\n" %SCRIPT
		print "Usage: boot.img\n"
		sys.exit(0)

	IMAGE_FN = sys.argv[1]
	if not os.path.exists(IMAGE_FN):
		goto_exit("%s not found!" %IMAGE_FN)
######################################################################
'''
=format (from bootimg.h)
** +-----------------+
** | boot header     | 1 page
** +-----------------+
** | kernel          | n pages
** +-----------------+
** | ramdisk         | m pages
** +-----------------+
** | second stage    | o pages
** +-----------------+
**
** n = (kernel_size + page_size - 1) / page_size
** m = (ramdisk_size + page_size - 1) / page_size
** o = (second_size + page_size - 1) / page_size
'''
## Main Code
def main():
	parse_cmdline()
	parse_header(IMAGE_FN)
	
	n = int((KERNEL_SIZE + PAGE_SIZE - 1) / PAGE_SIZE)
	m = int((RAMDISK_SIZE + PAGE_SIZE - 1) / PAGE_SIZE)
	o = int((SECOND_SIZE + PAGE_SIZE - 1) / PAGE_SIZE)

	k_offset = PAGE_SIZE
	r_offset = k_offset + (n * PAGE_SIZE)
	s_offset = r_offset + (m * PAGE_SIZE)

	base = os.path.basename(IMAGE_FN)
	k_file = base + "-kernel"
	r_file = base + "-ramdisk.gz"
	r_file_bak = base + "-ramdisk"
	s_file = base + "-second.gz"

	# The kernel is always there
	print "Writing %s ..." %k_file
	dump_file(IMAGE_FN, k_file, k_offset, KERNEL_SIZE)
	print "Complete."

	# The ramdisk is always there
	print "Writing %s ..." %r_file
	dump_file(IMAGE_FN, r_file, r_offset, RAMDISK_SIZE)
	print "Gunzip %s  to %s..." %(r_file, r_file_bak)
	gunzip_file(r_file, r_file_bak)
	print "Complete."

	# The Second stage bootloader is optional
	if (SECOND_SIZE != 0):
		print "Writing %s ..." %s_file
		dump_file(IMAGE_FN, s_file, s_offset, SECOND_SIZE)
		print "Complete."
######################################################################
if __name__ == "__main__":
	main()
