#!/bin/fish
# Define wallets

set -l adminWallet "page rebuild web legend found regret swallow whale admit quarter month shoulder gossip coin quit genius timber jar beach distance identify labor amazing about alpha"
set -l adminAddr "RRXY3RSR2XRMJG3ZOBBTYXWLU6SKG3YJGUEEN4CC6MHOMCF4V2Q2ZYN4R4"

set -l seller1Walet "nurse stuff velvet couch outside invite zone member peanut elevator rigid question morning width earn outer kit shine asthma stamp wisdom feed casual able cement"
set -l seller1Addr "MSNHPFV3UYDPSSPVMJ7O3HX3CDXCIK2PUCTBB5GHBYAPLASK5TLEKP3PWI"

set -l buyer1Wallet "episode bean pipe real clown slow music faint stand panic atom ladder critic fire mixture sick adapt camp endless brother sketch wing metal able time"
set -l buyer1Addr "YI2LVJHTP65JIUWPYCLI6IIO3KDKW3CYKFAQ27UUFGTUWCBEMTUK43CTF4"
echo "Generating wallets"

sandbox/./sandbox goal account import  -m $adminWallet
sandbox/./sandbox goal account rename Unnamed-0 aMart-Admin

sandbox/./sandbox goal account import -m $seller1Walet
sandbox/./sandbox goal account rename Unnamed-0 aMart-Seller1

sandbox/./sandbox goal account import -m $buyer1Wallet
sandbox/./sandbox goal account rename Unnamed-0 aMart-Buyer1

echo "Sending algos"
sandbox/./sandbox goal clerk send -a "1008035622062" -f PWKDDC7PGXCEEBL4MSVDWLYDZN6RJ2T4CELEP6PLKZZI5DXV5GFH7J6YKU -t $adminAddr
sandbox/./sandbox goal clerk send -a "1008035622062" -f TP7FTYCJRG6VDD4EJHHFTP7K5HLCTSY4EPRDHD2LQH7HG6OPCE5ZZMLD4E -t $seller1Addr
sandbox/./sandbox goal clerk send -a "5000000000" -f WBPK76F6U2VYPSUDHSNV3BFVYOMXP4LXM32UG7PFTS7ENEOVVNQZ576RHE -t $buyer1Addr
sandbox/./sandbox goal account list
