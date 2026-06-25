view: dwell_metrics {
  sql_table_name: oxagon.dwell_windows ;;

  dimension: tenant_id {
    type: string
    sql: ${TABLE}.tenant_id ;;
  }

  dimension: container_number {
    primary_key: yes
    type: string
    sql: ${TABLE}.container_number ;;
  }

  dimension_group: gate_in {
    type: time
    timeframes: [raw, time, date, week, month, hour_of_day]
    sql: ${TABLE}.gate_in_at ;;
  }

  dimension_group: gate_out {
    type: time
    timeframes: [raw, time, date]
    sql: ${TABLE}.gate_out_at ;;
  }

  measure: avg_dwell_hours {
    type: average
    sql: EXTRACT(EPOCH FROM (${TABLE}.gate_out_at - ${TABLE}.gate_in_at)) / 3600.0 ;;
    value_format_name: decimal_1
  }

  measure: p95_dwell_hours {
    type: number
    sql: percentile_cont(0.95) WITHIN GROUP (
            ORDER BY EXTRACT(EPOCH FROM (${TABLE}.gate_out_at - ${TABLE}.gate_in_at)) / 3600.0
         ) ;;
    value_format_name: decimal_1
  }

  measure: container_count {
    type: count
  }
}
