#!/usr/bin/env fish

set -g temp ".temp"
set -g cache "$temp/cache"              # Cache file
set -g smartcontract "$temp/smartcontract"
set -g tokens "$temp/tokens"
set -g s "sandbox/./sandbox"

# DEFINE accounts type based in the index
set -g ADMIN 1
set -g SELLER 2
set -g BUYER 3

# Check if the temp file exist otherwise create it
if not test -d $temp
    mkdir $temp
end

# activate conda beaker env
conda activate beaker
################
# UI functions #
################
function title
    set -l t $argv[1]
    set_color -u
    set_color -o $fish_color_error; echo $t
    set_color normal
    echo ""
end
function subTitle
    set -l t $argv[1]
    set_color -u
    set_color -o $fish_color_cwd; echo $t
    set_color normal
    echo ""
end
function menuTitle
    set -l m $argv[1]
    set_color $fish_color_command; echo $m
    set_color normal
end


function cleanCache
    # remove the cache file
    rm $cache
end

function resetSandbox
    $s reset
end
function getAccounts
    # Get Sandbox accounts
    $s goal account list > $cache
    cat $cache | awk '{print $2}'
    cleanCache
end
function getAccountList
    $s goal account list
end
function getAddressInfo
    set -l addr $argv[1]
    title "Information about $addr"
    $s goal account info -a $addr
end

function createStableCoin
    # Create a stable coin
    set -l creator $argv[1]
    set -l name $argv[2]
    set -l unitname $argv[3]

    $s goal asset create --creator $creator --clawback $creator --decimals 6 --total 1000000000000000000 --name $name --unitname $unitname > $cache
    set -l asset (cat $cache | awk '{ if($1 == "Created") print$0 }' )
    set asset (string split ' ' $asset)
    echo "$unitname $asset[6]" >> $tokens
    echo $asset[6]
end

function optInAsset
    # Opt-in into an asset
    set -l addr $argv[1]
    set -l asset $argv[2]
    $s goal asset optin -a $addr --assetid $asset
end

function sendAsset
    set -l from $argv[1]
    set -l to $argv[2]
    set -l asset $argv[3]
    set -l amount $argv[4]
    $s goal asset send -a $amount --assetid $asset -f $from -t $to
end

function deployContract
    # Deploy the smartcontract
    set -l t (cat $tokens | awk '{print $2}')
    python deploy.py $t > $smartcontract
end

function updateContract
    if test -e $smartcontract
        set -l data (cat $smartcontract | awk '{if($1 == "app_id") print$0}')
        set -l app (string split ' ' $data)
        python update.py $app[2]
    else
        echo "No smartcontract deployed"
    end
end

function appInfo
    if test -e $smartcontract
        set -l data (cat $smartcontract | awk '{if($1 == "app_id") print$0}')
        set -l app (string split ' ' $data)

        title "Application Info"
        $s goal app info --app-id $app[2]
    else
        echo "No smartcontract deployed"
    end
end
function appGlobal
    if test -e $smartcontract
        set -l data (cat $smartcontract | awk '{if($1 == "app_id") print$0}')
        set -l app (string split ' ' $data)

        title "Application Global State"
        $s goal app read --app-id $app[2] --global
    else
        echo "No smartcontract deployed"
    end
end
function appBoxes
    if test -e $smartcontract
        set -l data (cat $smartcontract | awk '{if($1 == "app_id") print$0}')
        set -l app (string split ' ' $data)

        title "Application Boxes"
        $s goal app box list --app-id $app[2]
    else
        echo "No smartcontract deployed"
    end
end
function appBalance
    if test -e $smartcontract
        set -l data (cat $smartcontract | awk '{if($1 == "app_addr") print$0}')
        set -l app (string split ' ' $data)

        title "Application $app[2]"
        subTitle "Application Asset Info"
        $s goal account info -a $app[2]
        echo ""
        subTitle "Application Algo Balance"
        $s goal account balance -a $app[2]
        echo ""
    else
        echo "No smartcontract deployed"
    end
end
#####################
# Load the accounts #
#####################

set -g accounts (getAccounts)               # Save the account into a list

#########
# Menus #
#########
function subMenuAccounts
    set -l i 1
    clear
    while test $i -gt 0
        title "-- ACCOUNTS MENU --"
        menuTitle "1) Admin"
        menuTitle "2) Seller"
        menuTitle "3) Buyer"
        menuTitle "4) ALL"
        menuTitle "0) Back"
        echo ""
        read i
        if test $i -gt 0; and test $i -le 3
            clear
            getAddressInfo $accounts[$i]
        else if test $i -eq 4
            clear
            getAccountList
        end
    end
end

function subMenuResetApp
    # Remove the tokens file
    if test -e $tokens
        rm $tokens
    end
    
    clear
    resetSandbox
    clear

    title " -- Creating USDC token"
    sleep 3
    set -l usdc (createStableCoin $accounts[$ADMIN] "Circle USD" USDC)
    clear

    title " -- Creating USDT token"
    sleep 3
    set -l usdt (createStableCoin $accounts[$ADMIN] "Tether" USDT)
    clear

    # SELLER ACCOUNT
    title " -- Opt-in USDC - $accounts[$SELLER]"
    sleep 3
    optInAsset $accounts[$SELLER] $usdc
    clear

    title " -- Sending USDC - $accounts[$SELLER]"
    sleep 3
    sendAsset $accounts[$ADMIN] $accounts[$SELLER] $usdc 100000000000
    clear

    title " -- Opt-in USDT - $accounts[$SELLER]"
    sleep 3
    optInAsset $accounts[$SELLER] $usdt
    clear

    title " -- Sending USDC - $accounts[$SELLER]"
    sleep 3
    sendAsset $accounts[$ADMIN] $accounts[$SELLER] $usdt 100000000000
    clear

    # BUYER ACCOUNT
    title " -- Opt-in USDC - $accounts[$BUYER]"
    sleep 3
    optInAsset $accounts[$BUYER] $usdc
    clear

    title " -- Sending USDC - $accounts[$BUYER]"
    sleep 3
    sendAsset $accounts[$ADMIN] $accounts[$BUYER] $usdc 100000000000
    clear

    title " -- Opt-in USDT - $accounts[$BUYER]"
    sleep 3
    optInAsset $accounts[$BUYER] $usdt
    clear

    title " -- Sending USDC - $accounts[$BUYER]"
    sleep 3
    sendAsset $accounts[$ADMIN] $accounts[$BUYER] $usdt 100000000000
    clear


end

function subMenuSmartContractApp
    # Menu for the smartcontract app
    set -l input 1
    while test $input -gt 0
        clear
        title "-- SmartContract App Menu --"
        menuTitle "1) Deploy APP"
        menuTitle "2) Udate APP"
        menuTitle "3) Show APP ID | APP ADDR | APP LICENSE"
        menuTitle "4) App Info"
        menuTitle "5) App Global State"
        menuTitle "6) App Boxes"
        menuTitle "7) App Balance"
        menuTitle "0) Back"
        echo ""
        read input
        if test $input -eq 1
            clear
            title "-- Deploying smartconract ..."
            deployContract
            read
        else if test $input -eq 2
            clear
            title "-- Updating smartcontract ..."
            updateContract

        else if test $input -eq 3
            clear
            title "-- Application Config"
            cat $smartcontract
            read
        else if test $input -eq 4
            clear
            appInfo
            read
        else if test $input -eq 5
            clear
            appGlobal
            read
        else if test $input -eq 6
            clear
            appBoxes
            read
        else if test $input -eq 7
            clear
            appBalance
            read
        else
            clear
        end
    end
end
function mainMenuApp
    set -l input 1
    while test $input -gt 0
        clear
        title "-- APPLICATION MENU --"
        menuTitle "1) Accounts"
        menuTitle "2) Application"
        menuTitle "3) Reset"
        menuTitle "0) Exit"
        echo ""
        read input
        if test $input -eq 1
            echo "menu"
            subMenuAccounts
        else if test $input -eq 2
            subMenuSmartContractApp
        else if test $input -eq 3
            subMenuResetApp

        else
            clear
            return 0
        end
    end

end




set -l o $argv[1]

if test "$o" = "app"
    clear
    mainMenuApp
else
    echo "Bye"
end
