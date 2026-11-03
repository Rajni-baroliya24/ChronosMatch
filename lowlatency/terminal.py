"""Curses dashboard; deliberately outside the matching process."""
import curses


def draw(screen, metrics, orders, trades, history):
    with metrics.get_lock():
        values = list(metrics[:])
    history.append(values[3] / 1000)
    del history[:-48]
    height, width = screen.getmaxyx()
    screen.erase()
    rows = [
        'ChronosMatch | Cython + mmap | q: stop ingestion and drain',
        f'Orders processed: {values[0]:,}   Trades: {values[1]:,}   SQLite committed: {values[2]:,}',
        f'Latest enqueue-to-match: {values[3]/1000:.2f} us   Native call: {values[4]/1000:.2f} us',
        f'AAPL bid: {values[6]/100:.2f} x {values[7]}   Ask: {values[8]/100:.2f} x {values[9]}',
        f'Order ring pending: {orders.counts()["pending"]}   Trade ring pending: {trades.counts()["pending"]}',
        f'WHALE SWEEPS (3+ fills): {values[5]}',
        'Recent latency (each star is a sampled update; auto-scaled):',
    ]
    maximum = max(history, default=1) or 1
    for value in history[-max(0, height - 10):]:
        rows.append(f'{value:9.1f} us ' + '*' * max(1, int(value / maximum * max(1, min(width - 18, 50)))))
    if curses.has_colors():
        curses.start_color()
        curses.init_pair(1, curses.COLOR_YELLOW, curses.COLOR_BLACK)
    for index, row in enumerate(rows[:max(0, height - 1)]):
        try:
            attribute = curses.A_BOLD if index == 0 or (index == 5 and values[5]) else 0
            if index == 5 and values[5] and curses.has_colors():
                attribute |= curses.color_pair(1)
            screen.addnstr(index, 0, row, max(0, width - 1), attribute)
        except curses.error:
            pass
    screen.refresh()
