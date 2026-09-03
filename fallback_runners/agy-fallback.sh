#!/usr/bin/env bash
# Antigravity CLI (AGY) Auto-Fallback & Quota Resilience Manager for Linux / VPS
# Otomatis beralih ke model alternatif saat Individual quota reached

AGY_BIN=$(which agy 2>/dev/null || echo "$HOME/.local/bin/agy")
MODEL_CHAIN=("gemini-3.8-flash-high" "claude-sonnet-4-6" "gemini-3.7-flash-high" "gemini-3.1-pro-high" "gpt-oss-120b-medium")

test_model() {
    local model="$1"
    local out
    out=$("$AGY_BIN" -p "Jawab singkat: OK" --model "$model" 2>&1)
    if echo "$out" | grep -Eqi "quota reached|upgrade your subscription|rate limit|exhausted|429 Too Many"; then
        return 1
    fi
    if [ $? -eq 0 ] && [ -n "$out" ]; then
        return 0
    fi
    return 1
}

show_status() {
    echo -e "\n======================================================="
    echo -e "     ANTIGRAVITY CLI (AGY) MODEL QUOTA HEALTH CHECK   "
    echo -e "======================================================="
    for m in "${MODEL_CHAIN[@]}"; do
        echo -n "Checking [$m] ... "
        if test_model "$m"; then
            echo -e "\e[32mREADY (Active & Quota Available)\e[0m"
        else
            echo -e "\e[31mEXHAUSTED / LIMITED\e[0m"
        fi
    done
    echo -e "-------------------------------------------------------\n"
}

find_first_model() {
    echo -e "\e[33m[AGY-FALLBACK] Memindai model dengan kuota aktif...\e[0m" >&2
    for m in "${MODEL_CHAIN[@]}"; do
        echo -n "  - Menguji $m ... " >&2
        if test_model "$m"; then
            echo -e "\e[32mTERSEDIA!\e[0m" >&2
            echo "$m"
            return 0
        else
            echo -e "\e[31mLIMIT\e[0m" >&2
        fi
    done
    echo "${MODEL_CHAIN[0]}"
}

# Routing
if [ $# -eq 0 ]; then
    BEST=$(find_first_model)
    echo -e "\n\e[36m[AGY-FALLBACK] Memulai sesi interaktif dengan model: $BEST\e[0m\n"
    exec "$AGY_BIN" --model "$BEST"
fi

case "$1" in
    check|status)
        show_status
        exit 0
        ;;
    -c|--continue|continue|resume)
        BEST=$(find_first_model)
        echo -e "\n\e[32m[AGY-FALLBACK] Melanjutkan sesi sebelumnya dengan model: $BEST\e[0m\n"
        exec "$AGY_BIN" -c --model "$BEST"
        ;;
esac

# Execution mode with auto-retry
TARGET_ARGS=("$@")
echo -e "\e[36m[AGY-FALLBACK] Menjalankan perintah AGY dengan auto-fallback...\e[0m"

for m in "${MODEL_CHAIN[@]}"; do
    echo -e "\n\e[90m[AGY-FALLBACK] Mencoba model: $m\e[0m"
    OUT=$("$AGY_BIN" "${TARGET_ARGS[@]}" --model "$m" 2>&1)
    CODE=$?

    if echo "$OUT" | grep -Eqi "quota reached|upgrade your subscription|rate limit|exhausted|429 Too Many"; then
        echo -e "\e[31m[!] KUOTA HABIS pada model: $m\e[0m"
        echo -e "\e[33m    Pesan: Individual quota reached. Otomatis fallback ke model berikutnya...\e[0m"
        TARGET_ARGS=("-c" "${TARGET_ARGS[@]}")
        continue
    else
        echo "$OUT"
        exit $CODE
    fi
done

echo -e "\n\e[31m[AGY-FALLBACK] Semua model dalam rantai fallback telah mencapai batas kuota.\e[0m"
exit 1
