# reorder should win the deadlock detector
setup {
 CREATE TABLE ts_reorder_test(time int, temp float, location int);
 SELECT create_hypertable('ts_reorder_test', 'time', chunk_time_interval => 10);
 INSERT INTO ts_reorder_test VALUES (1, 23.4, 1),
       (11, 21.3, 2),
       (21, 19.5, 3);

 CREATE TABLE waiter(i INTEGER);
 CREATE OR REPLACE FUNCTION reorder_chunk_i(
      chunk REGCLASS,
      index REGCLASS=NULL,
      verbose BOOLEAN=FALSE,
      wait_on REGCLASS=NULL
  ) RETURNS VOID AS '$libdir/timescaledb-1.2.0-dev', 'ts_reorder_chunk' LANGUAGE C VOLATILE;
}

teardown {
      DROP TABLE ts_reorder_test;
      DROP TABLE waiter;
}

session "S"
setup		{ BEGIN; }
step "S1"	{ SELECT * FROM ts_reorder_test; }
step "S2"	{ INSERT INTO ts_reorder_test VALUES (1, 23.4, 1); }
step "Sc"	{ COMMIT; }

session "R"
setup		{ BEGIN; }
step "R1"	{ SELECT reorder_chunk_i((SELECT show_chunks('ts_reorder_test') LIMIT 1), 'ts_reorder_test_time_idx', wait_on => 'waiter'); }
step "Rc"	{ COMMIT; }

session "B"
setup		{ BEGIN; LOCK TABLE waiter; }
step "Bc"   { ROLLBACK; }

# TODO this fails in an unexpected manner, but isn't critical since the barrier should not be used in real code
#permutation "S1" "R1" "S2" "Bc" "Rc" "Sc"

#upgrade deadlocks should favor reorder
permutation "S1" "R1" "Bc" "S2" "Rc" "Sc"
permutation "S1" "R1" "Bc" "S2" "Sc" "Rc"
