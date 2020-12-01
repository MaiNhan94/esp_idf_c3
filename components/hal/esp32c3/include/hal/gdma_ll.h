// Copyright 2020 Espressif Systems (Shanghai) PTE LTD
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
#pragma once

#include <stdint.h>
#include <stdbool.h>
#include "soc/gdma_struct.h"
#include "soc/gdma_reg.h"
#include "soc/gdma_caps.h"

#ifdef __cplusplus
extern "C" {
#endif

#define GDMA_LL_EVENT_TX_FIFO_UDF   (1<<12)
#define GDMA_LL_EVENT_TX_FIFO_OVF   (1<<11)
#define GDMA_LL_EVENT_RX_FIFO_UDF   (1<<10)
#define GDMA_LL_EVENT_RX_FIFO_OVF   (1<<9)
#define GDMA_LL_EVENT_TX_TOTAL_EOF  (1<<8)
#define GDMA_LL_EVENT_RX_DESC_EMPTY (1<<7)
#define GDMA_LL_EVENT_TX_DESC_ERROR (1<<6)
#define GDMA_LL_EVENT_RX_DESC_ERROR (1<<5)
#define GDMA_LL_EVENT_TX_EOF        (1<<4)
#define GDMA_LL_EVENT_TX_DONE       (1<<3)
#define GDMA_LL_EVENT_RX_ERR_EOF    (1<<2)
#define GDMA_LL_EVENT_RX_SUC_EOF    (1<<1)
#define GDMA_LL_EVENT_RX_DONE       (1<<0)

#define GDMA_LL_TRIG_SRC_SPI2    (0)
#define GDMA_LL_TRIG_SRC_UART    (2)
#define GDMA_LL_TRIG_SRC_I2S0    (3)
#define GDMA_LL_TRIG_SRC_AES     (6)
#define GDMA_LL_TRIG_SRC_SHA     (7)
#define GDMA_LL_TRIG_SRC_ADC_DAC (8)

///////////////////////////////////// Common /////////////////////////////////////////
/**
 * @brief Enable DMA channel M2M mode (TX channel n forward data to RX channel n), disabled by default
 */
static inline void gdma_ll_enable_m2m_mode(gdma_dev_t *dev, uint32_t channel, bool enable)
{
    dev->channel[channel].in.in_conf0.mem_trans_en = enable;
    if (enable) {
        // only have to give it a valid value
        dev->channel[channel].in.in_peri_sel.sel = 0;
        dev->channel[channel].out.out_peri_sel.sel = 0;
    }
}

/**
 * @brief Get DMA interrupt status word
 */
static inline uint32_t gdma_ll_get_interrupt_status(gdma_dev_t *dev, uint32_t channel)
{
    return dev->intr[channel].st.val;
}

/**
 * @brief Enable DMA interrupt
 */
static inline void gdma_ll_enable_interrupt(gdma_dev_t *dev, uint32_t channel, uint32_t mask, bool enable)
{
    if (enable) {
        dev->intr[channel].ena.val |= mask;
    } else {
        dev->intr[channel].ena.val &= ~mask;
    }
}

/**
 * @brief Clear DMA interrupt
 */
static inline void gdma_ll_clear_interrupt_status(gdma_dev_t *dev, uint32_t channel, uint32_t mask)
{
    dev->intr[channel].clr.val = mask;
}

/**
 * @brief Enable DMA clock gating
 */
static inline void gdma_ll_enable_clock(gdma_dev_t *dev, bool enable)
{
    dev->misc_conf.clk_en = enable;
}

///////////////////////////////////// RX /////////////////////////////////////////
/**
 * @brief Enable DMA RX channel to check the owner bit in the descriptor, disabled by default
 */
static inline void gdma_ll_rx_enable_owner_check(gdma_dev_t *dev, uint32_t channel, bool enable)
{
    dev->channel[channel].in.in_conf1.in_check_owner = enable;
}

/**
 * @brief Enable DMA RX channel burst reading data, disabled by default
 */
static inline void gdma_ll_rx_enable_data_burst(gdma_dev_t *dev, uint32_t channel, bool enable)
{
    dev->channel[channel].in.in_conf0.in_data_burst_en = enable;
}

/**
 * @brief Enable DMA RX channel burst reading descriptor link, disabled by default
 */
static inline void gdma_ll_rx_enable_descriptor_burst(gdma_dev_t *dev, uint32_t channel, bool enable)
{
    dev->channel[channel].in.in_conf0.indscr_burst_en = enable;
}

/**
 * @brief Reset DMA RX channel FSM and FIFO pointer
 */
static inline void gdma_ll_rx_reset_channel(gdma_dev_t *dev, uint32_t channel)
{
    dev->channel[channel].in.in_conf0.in_rst = 1;
    dev->channel[channel].in.in_conf0.in_rst = 0;
}

/**
 * @brief Check if DMA RX FIFO is full
 * @param fifo_level only supports level 1
 */
static inline bool gdma_ll_rx_is_fifo_full(gdma_dev_t *dev, uint32_t channel, uint32_t fifo_level)
{
    return dev->channel[channel].in.infifo_status.val & 0x01;
}

/**
 * @brief Check if DMA RX FIFO is empty
 * @param fifo_level only supports level 1
 */
static inline bool gdma_ll_rx_is_fifo_empty(gdma_dev_t *dev, uint32_t channel, uint32_t fifo_level)
{
    return dev->channel[channel].in.infifo_status.val & 0x02;
}

/**
 * @brief Get number of bytes in RX FIFO
 * @param fifo_level only supports level 1
 */
static inline uint32_t gdma_ll_rx_get_fifo_bytes(gdma_dev_t *dev, uint32_t channel, uint32_t fifo_level)
{
    return dev->channel[channel].in.infifo_status.infifo_cnt;
}

/**
 * @brief Pop data from DMA RX FIFO
 */
static inline uint32_t gdma_ll_rx_pop_data(gdma_dev_t *dev, uint32_t channel)
{
    dev->channel[channel].in.in_pop.infifo_pop = 1;
    return dev->channel[channel].in.in_pop.infifo_rdata;
}

/**
 * @brief Set the descriptor link base address for RX channel
 */
static inline void gdma_ll_rx_set_desc_addr(gdma_dev_t *dev, uint32_t channel, uint32_t addr)
{
    dev->channel[channel].in.in_link.addr = addr;
}

/**
 * @brief Start dealing with RX descriptors
 */
static inline void gdma_ll_rx_start(gdma_dev_t *dev, uint32_t channel)
{
    dev->channel[channel].in.in_link.start = 1;
}

/**
 * @brief Stop dealing with RX descriptors
 */
static inline void gdma_ll_rx_stop(gdma_dev_t *dev, uint32_t channel)
{
    dev->channel[channel].in.in_link.stop = 1;
}

/**
 * @brief Restart a new inlink right after the last descriptor
 */
static inline void gdma_ll_rx_restart(gdma_dev_t *dev, uint32_t channel)
{
    dev->channel[channel].in.in_link.restart = 1;
}

/**
 * @brief Enable DMA RX to return the address of current descriptor when receives error
 */
static inline void gdma_ll_rx_enable_auto_return(gdma_dev_t *dev, uint32_t channel, bool enable)
{
    dev->channel[channel].in.in_link.auto_ret = enable;
}

/**
 * @brief Check if DMA RX FSM is in IDLE state
 */
static inline bool gdma_ll_rx_is_fsm_idle(gdma_dev_t *dev, uint32_t channel)
{
    return dev->channel[channel].in.in_link.park;
}

/**
 * @brief Get RX success EOF descriptor's address
 */
static inline uint32_t gdma_ll_rx_get_success_eof_desc_addr(gdma_dev_t *dev, uint32_t channel)
{
    return dev->channel[channel].in.in_suc_eof_des_addr;
}

/**
 * @brief Get RX error EOF descriptor's address
 */
static inline uint32_t gdma_ll_rx_get_error_eof_desc_addr(gdma_dev_t *dev, uint32_t channel)
{
    return dev->channel[channel].in.in_err_eof_des_addr;
}

/**
 * @brief Get current RX descriptor's address
 */
static inline uint32_t gdma_ll_rx_get_current_desc_addr(gdma_dev_t *dev, uint32_t channel)
{
    return dev->channel[channel].in.in_dscr;
}

/**
 * @brief Set priority for DMA RX channel
 */
static inline void gdma_ll_rx_set_priority(gdma_dev_t *dev, uint32_t channel, uint32_t prio)
{
    dev->channel[channel].in.in_pri.rx_pri = prio;
}

/**
 * @brief Connect DMA RX channel to a given peripheral
 */
static inline void gdma_ll_rx_connect_to_periph(gdma_dev_t *dev, uint32_t channel, uint32_t periph_id)
{
    dev->channel[channel].in.in_peri_sel.sel = periph_id;
}

///////////////////////////////////// TX /////////////////////////////////////////
/**
 * @brief Enable DMA TX channel to check the owner bit in the descriptor, disabled by default
 */
static inline void gdma_ll_tx_enable_owner_check(gdma_dev_t *dev, uint32_t channel, bool enable)
{
    dev->channel[channel].out.out_conf1.out_check_owner = enable;
}

/**
 * @brief Enable DMA TX channel burst sending data, disabled by default
 */
static inline void gdma_ll_tx_enable_data_burst(gdma_dev_t *dev, uint32_t channel, bool enable)
{
    dev->channel[channel].out.out_conf0.out_data_burst_en = enable;
}

/**
 * @brief Enable DMA TX channel burst reading descriptor link, disabled by default
 */
static inline void gdma_ll_tx_enable_descriptor_burst(gdma_dev_t *dev, uint32_t channel, bool enable)
{
    dev->channel[channel].out.out_conf0.outdscr_burst_en = enable;
}

/**
 * @brief Set TX channel EOF mode
 */
static inline void gdma_ll_tx_set_eof_mode(gdma_dev_t *dev, uint32_t channel, uint32_t mode)
{
    dev->channel[channel].out.out_conf0.out_eof_mode = mode;
}

/**
 * @brief Enable DMA TX channel automatic write results back to descriptor after all data has been sent out, disabled by default
 */
static inline void gdma_ll_tx_enable_auto_write_back(gdma_dev_t *dev, uint32_t channel, bool enable)
{
    dev->channel[channel].out.out_conf0.out_auto_wrback = enable;
}

/**
 * @brief Reset DMA TX channel FSM and FIFO pointer
 */
static inline void gdma_ll_tx_reset_channel(gdma_dev_t *dev, uint32_t channel)
{
    dev->channel[channel].out.out_conf0.out_rst = 1;
    dev->channel[channel].out.out_conf0.out_rst = 0;
}

/**
 * @brief Check if DMA TX FIFO is full
 * @param fifo_level only supports level 1
 */
static inline bool gdma_ll_tx_is_fifo_full(gdma_dev_t *dev, uint32_t channel, uint32_t fifo_level)
{
    return dev->channel[channel].out.outfifo_status.val & 0x01;
}

/**
 * @brief Check if DMA TX FIFO is empty
 * @param fifo_level only supports level 1
 */
static inline bool gdma_ll_tx_is_fifo_empty(gdma_dev_t *dev, uint32_t channel, uint32_t fifo_level)
{
    return dev->channel[channel].out.outfifo_status.val & 0x02;
}

/**
 * @brief Get number of bytes in TX FIFO
 * @param fifo_level only supports level 1
 */
static inline uint32_t gdma_ll_tx_get_fifo_bytes(gdma_dev_t *dev, uint32_t channel, uint32_t fifo_level)
{
    return dev->channel[channel].out.outfifo_status.outfifo_cnt;
}

/**
 * @brief Push data into DMA TX FIFO
 */
static inline void gdma_ll_tx_push_data(gdma_dev_t *dev, uint32_t channel, uint32_t data)
{
    dev->channel[channel].out.out_push.outfifo_wdata = data;
    dev->channel[channel].out.out_push.outfifo_push = 1;
}

/**
 * @brief Set the descriptor link base address for TX channel
 */
static inline void gdma_ll_tx_set_desc_addr(gdma_dev_t *dev, uint32_t channel, uint32_t addr)
{
    dev->channel[channel].out.out_link.addr = addr;
}

/**
 * @brief Start dealing with TX descriptors
 */
static inline void gdma_ll_tx_start(gdma_dev_t *dev, uint32_t channel)
{
    dev->channel[channel].out.out_link.start = 1;
}

/**
 * @brief Stop dealing with TX descriptors
 */
static inline void gdma_ll_tx_stop(gdma_dev_t *dev, uint32_t channel)
{
    dev->channel[channel].out.out_link.stop = 1;
}

/**
 * @brief Restart a new outlink right after the last descriptor
 */
static inline void gdma_ll_tx_restart(gdma_dev_t *dev, uint32_t channel)
{
    dev->channel[channel].out.out_link.restart = 1;
}

/**
 * @brief Check if DMA TX FSM is in IDLE state
 */
static inline bool gdma_ll_tx_is_fsm_idle(gdma_dev_t *dev, uint32_t channel)
{
    return dev->channel[channel].out.out_link.park;
}

/**
 * @brief Get TX EOF descriptor's address
 */
static inline uint32_t gdma_ll_tx_get_eof_desc_addr(gdma_dev_t *dev, uint32_t channel)
{
    return dev->channel[channel].out.out_eof_des_addr;
}

/**
 * @brief Get current TX descriptor's address
 */
static inline uint32_t gdma_ll_tx_get_current_desc_addr(gdma_dev_t *dev, uint32_t channel)
{
    return dev->channel[channel].out.out_dscr;
}

/**
 * @brief Set priority for DMA TX channel
 */
static inline void gdma_ll_tx_set_priority(gdma_dev_t *dev, uint32_t channel, uint32_t prio)
{
    dev->channel[channel].out.out_pri.tx_pri = prio;
}

/**
 * @brief Connect DMA TX channel to a given peripheral
 */
static inline void gdma_ll_tx_connect_to_periph(gdma_dev_t *dev, uint32_t channel, uint32_t periph_id)
{
    dev->channel[channel].out.out_peri_sel.sel = periph_id;
}

#ifdef __cplusplus
}
#endif
