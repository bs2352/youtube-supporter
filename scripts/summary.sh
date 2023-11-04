#!/bin/sh

VID_LIST="../vid.txt" # 動画IDのリスト
SUMMARY_DIR="../data/summaries" # 要約の保存先


main() {
    echo $1
    case $1 in
        "summarize" ) summarize ;;
        "summary" ) summary ;;
        "list" ) list ;;
        * ) list;;
    esac
}


# 動画IDリストの動画を全て要約する
summarize() {
    for vid in `cat $VID_LIST`
    do
        cur_dir=`pwd`
        cd ..
        python -m yts --summary --vid $vid
        cd $cur_dir
    done
}


# 要約ディレクトリにある全ての要約を一覧表示する
list() {
    for vid in `ls $SUMMARY_DIR`
    do
        summary_file="$SUMMARY_DIR/$vid"
        title=`cat $summary_file | jq | grep title | cut -d ':' -f2 | sed -e 's/,$//' | sed -e 's/^[ \t]*//' | sed -e 's/^"//' | sed -e 's/"$//'`
        author=`cat $summary_file | jq | grep author | cut -d ':' -f2 | sed -e 's/,$//' | sed -e 's/^[ \t]*//' | sed -e 's/^"//' | sed -e 's/"$//'`
        echo "$vid\t$author\t$title"
    done
}

# 要約ディレクトリの要約を順番に表示する
summary() {
    for vid in `ls $SUMMARY_DIR`
    do
        echo $vid
        summary_file="$SUMMARY_DIR/$vid"
        cat $summary_file | jq | less
    done
}


main $1